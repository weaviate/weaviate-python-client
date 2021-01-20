import time
import threading
import sys
from typing import Callable
import weaviate
from .submit import SubmitBatches, SubmitBatchesException


class Batcher:
    """
    Manages batches and batch loading. Autocommits both Objects and References
    when the batcher reacher the allocated size. It resets after the batch is
    loaded to the weaviate, and can be reused.
    """

    def __init__(self,
            client: weaviate.Client,
            batch_size: int=512,
            verbose: bool=False,
            auto_commit_timeout: float=-1.0,
            max_backoff_time: int=300,
            max_request_retries: int=4,
            return_values_callback: Callable=None
        ):
        """
        Initialization of a Batcher class instance.

        Parameters
        ----------
        client : weaviate.Client
            The weaviate client for which to use the Batcher.
        batch_size : int, optional
            Total batcher size, i.e. "objects" batch size + "references" batch size,
            by default 512.
        verbose : bool, optional
            If True the batcher prints statuses of many steps.
            e.g. the return status of the batches,
            by default False.
        auto_commit_timeout : float, optional
            Time, in seconds, the batcher waits before loading all the data,
            no matter how big the batch size. Deactivated when <= 0,
            by default -1.0.
        max_backoff_time : int, optional
            Exponential backoff will never exceed this time in seconds,
            by default 300
        max_request_retries : int, optional
            States how often a request is retried before it is considered as failed,
            by default 4
        return_values_callback : Callable, optional
            If not none this function is called with the return values every time a
            batch is submitted.
            CAUTION if you use this together with the 'auto_commit_timeout'
            you need to ensure thread safety on the callback.
            by default None.
        """

        self._client = client
        # New batches
        self._objects_batch = weaviate.batch.ObjectsBatchRequest()
        self._reference_batch = weaviate.batch.ReferenceBatchRequest()
        # Submission fails are batches that where tried to be submitted but gave errors.
        # They are stored in an extra list with tuples (submission function, batch data)
        # So that they can be submitted on a later moment.
        self._submission_fails = []

        # Configuration
        self._batch_size = batch_size
        self._print_verbose_activated = verbose
        self._submit_batches = SubmitBatches(max_backoff_time, max_request_retries, self._print_verbose_activated)
        self._return_values_callback = return_values_callback

        # Auto commit info
        self._commit_lock: threading.Lock = threading.Lock()
        self._last_update = time.time()
        self._auto_commit_timeout = auto_commit_timeout
        self._auto_commit_watchdog = None
        if self._auto_commit_timeout > 0:
            self._auto_commit_watchdog = AutoCommitWatchdog(self)
            self._auto_commit_watchdog.start()

    def __enter__(self):
        return self

    def update_batches(self) -> None:
        """
        Forces an update of the batches no matter the current batch size.
        Prints errors if there are any.
        """
        with self._commit_lock:
            self._update_batches_force()

    def _update_batch_object(self, create_function, batch_data):
        """ Tries to send the data to the given function.
            Retains the function and data in failed submissions list if not successful.

        :param create_function:
        :param batch_data:
        :return:
        """

        try:
            self._submit_batches.submit_update(create_function, batch_data)
        except SubmitBatchesException:
            print("Error: Object batch was not added after max retries. Will retry with next batch submit")
            self._submission_fails.append((create_function, batch_data))
        else:
            if self._print_verbose_activated:
                print("Updated object batch successfully")

    def _retry_failed_submissions(self):
        """ Tries to resubmit failed submissions
        :return:
        """
        still_failing = []
        for create_func, batch_data in self._submission_fails:
            try:
                self._submit_batches.submit_update(create_func, batch_data)
            except SubmitBatchesException:
                still_failing.append((create_func, batch_data))
        if self._print_verbose_activated:
            if len(self._submission_fails) > 0:
                print("Of", len(self._submission_fails), "/", len(still_failing), "are still failing.")
        self._submission_fails = still_failing

    def _update_batches_force(self):
        if len(self._submission_fails) > 0:
            self._retry_failed_submissions()

        self._update_batch_object(self._client.batch.create, self._objects_batch)
        self._objects_batch = weaviate.batch.ObjectsBatchRequest()

        self._update_batch_object(self._client.batch.create, self._reference_batch)
        self._reference_batch = weaviate.batch.ReferenceBatchRequest()

        result_collection = self._submit_batches.pop_results()
        if self._return_values_callback is not None and len(result_collection) > 0:
            self._return_values_callback(result_collection)

        self._last_update = time.time()

    def _update_batch_if_necessary(self):
        """ Starts a batch load if the batch size is reached
        """
        if len(self._objects_batch) + len(self._reference_batch) >= self._batch_size:
            self._update_batches_force()

    def add_data_object(self, data_object, class_name, uuid=None):
        with self._commit_lock:
            self._last_update = time.time()
            self._objects_batch.add(data_object, class_name, uuid)
            self._update_batch_if_necessary()

    def add_reference(self, from_object_class_name, from_object_uuid, from_property_name,
                    to_object_uuid):
        with self._commit_lock:
            self._last_update = time.time()
            self._reference_batch.add(
                from_object_class_name=from_object_class_name,
                from_object_uuid=from_object_uuid,
                from_property_name=from_property_name,
                to_object_uuid=to_object_uuid
            )
            self._update_batch_if_necessary()

    def close(self):
        """ Closes this Batcher.
            Makes sure that all unfinished batches are loaded into weaviate.
            Batcher is not useable after closing.
        """

        # stop watchdog thread
        if self._auto_commit_watchdog is not None:
            with self._commit_lock:
                self._auto_commit_watchdog.is_closed = True

        retry_counter = 0
        while len(self._objects_batch) > 0 or len(self._reference_batch) > 0 or\
                        len(self._submission_fails) > 0:
            # update batches might have an connection error just retry until it is successful
            self.update_batches()
            retry_counter += 1
            if retry_counter > 500:
                print("CRITICAL ERROR objects can not be updated exit after 500 retries")
                sys.exit(5)

        self._reference_batch = None
        self._objects_batch = None
        self._client = None

    def __exit__(self, exception_type, exception_value, traceback):
        try:
            self.close()
        except Exception as e:
            print(e)


class AutoCommitWatchdog(threading.Thread):

    def __init__(self, batcher):
        """

        :param batcher:
        :type batcher: Batcher
        """
        threading.Thread.__init__(self)
        self.batcher = batcher
        self.is_closed = False

    def commit_batcher(self):
        with self.batcher._commit_lock:
            self.batcher._update_batches_force()

    def run(self):
        while not self.is_closed:
            now = time.time()
            delta = now - self.batcher._last_update
            if delta > self.batcher._auto_commit_timeout:
                self.commit_batcher()
            time.sleep(0.125)