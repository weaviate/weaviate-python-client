import weaviate
import time
from weaviate import SEMANTIC_TYPE_THINGS
import threading
from .submit import SubmitBatches, SubmitBatchesException


class Batcher:
    """ manages batches and batch loading
    """

    def __init__(self, client, batch_size=512, verbose=False, auto_commit_timeout=-1, return_values_callback=None,
                 max_backoff_time=300, max_request_retries=4):
        """

        :param client: weaviate client
        :type client: weaviate.Client
        :param batch_size: The batch size determines when a batch is send to weaviate.
        :type batch_size: int
        :param verbose: if true the batcher prints many steps e.g. the return status of the batches
        :type verbose: bool
        :param auto_commit_timeout: time in seconds the batcher waits before posting all the data,
                                    no matter how big the batch size. Deactivated when <= 0.
        :type auto_commit_timeout: float
        :param max_backoff_time: Exponential backoff will never exceed this time in seconds.
        :type max_backoff_time: int
        :param max_request_retries: States how often a request is retried before it counts as failed
        :type max_request_retries: int
        :param return_values_callback: If not none this function is called with the return values
                                       every time a batch is submitted.
                                       Caution if you use this together with the auto_commit_timeout
                                       you need to ensure thread safety on the callback.
        """

        self._client = client
        # New batches
        self._things_batch = weaviate.batch.ThingsBatchRequest()
        self._actions_batch = weaviate.batch.ActionsBatchRequest()
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

    def update_batches(self):
        """ Forces an update of the batches no matter the current batch size
            Prints errors if there are any
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

        self._update_batch_object(self._client.batch.create_things, self._things_batch)
        self._things_batch = weaviate.batch.ThingsBatchRequest()

        self._update_batch_object(self._client.batch.create_actions, self._actions_batch)
        self._actions_batch = weaviate.batch.ActionsBatchRequest()

        self._update_batch_object(self._client.batch.add_references, self._reference_batch)
        self._reference_batch = weaviate.batch.ReferenceBatchRequest()

        result_collection = self._submit_batches.pop_results()
        if self._return_values_callback is not None and len(result_collection) > 0:
            self._return_values_callback(result_collection)

        self._last_update = time.time()

    def _update_batch_if_necessary(self):
        """ Starts a batch load if the batch size is reached
        """
        if len(self._things_batch) + len(self._reference_batch) + len(self._actions_batch) >= self._batch_size:
            self._update_batches_force()

    def add_data_object(self, data_object, class_name, uuid=None, semantic_type=SEMANTIC_TYPE_THINGS):
        with self._commit_lock:
            self._last_update = time.time()
            if semantic_type == SEMANTIC_TYPE_THINGS:
                self._things_batch.add_thing(data_object, class_name, uuid)
                self._update_batch_if_necessary()
            else:
                self._actions_batch.add_action(data_object, class_name, uuid)
                self._update_batch_if_necessary()

    def add_reference(self, from_semantic_type, from_thing_class_name, from_thing_uuid, from_property_name,
                      to_semantic_type, to_thing_uuid):
        with self._commit_lock:
            self._last_update = time.time()
            self._reference_batch.add_reference(from_semantic_type=from_semantic_type,
                                                from_entity_class_name=from_thing_class_name,
                                                from_entity_uuid=from_thing_uuid,
                                                from_property_name=from_property_name,
                                                to_semantic_type=to_semantic_type,
                                                to_entity_uuid=to_thing_uuid)
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
        while len(self._things_batch) > 0 or len(self._actions_batch) > 0 or \
                len(self._reference_batch) > 0 or len(self._submission_fails) > 0:
            # update batches might have an connection error just retry until it is successful
            self.update_batches()
            retry_counter += 1
            if retry_counter > 500:
                print("CRITICAL ERROR things can not be updated exit after 500 retries")
                exit(5)

        self._reference_batch = None
        self._actions_batch = None
        self._things_batch = None
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