import weaviate
import time
from requests.exceptions import ReadTimeout, Timeout, ConnectionError
from weaviate import SEMANTIC_TYPE_THINGS, SEMANTIC_TYPE_ACTIONS
import threading


class Batcher:
    """ manages batches and batch loading
    """

    def __init__(self, client, batch_size=512, print_errors=False, auto_commit_timeout=-1, return_values_callback=None):
        """

        :param client: weaviate client
        :type client: weaviate.Client
        :param batch_size: The batch size determines when a batch is send to weaviate.
        :type batch_size: int
        :param print_errors: if true the return status of the batches get printed
        :type print_errors: bool
        :param auto_commit_timeout: time in seconds the batcher waits before posting all the data,
                                    no matter how big the batch size. Deactivated when <= 0.
        :type auto_commit_timeout: float
        :param return_values_callback: If not none this function is called with the return values
                                       every time a batch is submitted.
                                       Caution if you use this together with the auto_commit_timeout
                                       you need to ensure thread safety on the callback.
        """

        self._client = client
        self._things_batch = weaviate.batch.ThingsBatchRequest()
        self._actions_batch = weaviate.batch.ActionsBatchRequest()
        self._reference_batch = weaviate.batch.ReferenceBatchRequest()
        self._batch_size = batch_size
        self._print_errors_activated = print_errors
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

    def _print_errors(self, request_result):
        if not self._print_errors_activated:
            return

        for item in request_result:
            if len(item['result']) > 0:
                if not 'status' in item['result']:
                    print(item)
                    return

                if item['result']['status'] != 'SUCCESS':
                    print(item)

    def update_batches(self):
        """ Forces an update of the batches no matter the current batch size
            Prints errors if there are any
        """
        with self._commit_lock:
            self._update_batches_force()


    def _update_batches_force(self):
        result_collection = []
        if len(self._things_batch) > 0:
            try:
                result = self._client.batch.create_things(self._things_batch)
                if type(result) == list:
                    result_collection += result
            except (ConnectionError, Timeout, ReadTimeout, weaviate.UnexpectedStatusCodeException) as e:
                time.sleep(180.0)
                print("Exception in adding thing: ", e)
                return
            self._print_errors(result)
            self._things_batch = weaviate.batch.ThingsBatchRequest()
        if len(self._actions_batch) > 0:
            try:
                result = self._client.batch.create_actions(self._actions_batch)
                if type(result) == list:
                    result_collection += result
            except (ConnectionError, Timeout, ReadTimeout, weaviate.UnexpectedStatusCodeException) as e:
                time.sleep(180.0)
                print("Exception in adding action: ", e)
                return
            self._print_errors(result)
            self._actions_batch = weaviate.batch.ActionsBatchRequest()
        if len(self._reference_batch) > 0:
            try:
                result = self._client.batch.add_references(self._reference_batch)
                if type(result) == list:
                    result_collection += result
            except (ConnectionError, Timeout, ReadTimeout, weaviate.UnexpectedStatusCodeException) as e:
                # The connection error might just be a temporary thing lets sleep and return
                # The loading will be tried again next time something is added
                # Sleep for three minutes
                time.sleep(180.0)
                print("Exception in adding reference: ", e)
                return
            self._print_errors(result)
            self._reference_batch = weaviate.batch.ReferenceBatchRequest()

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
        while len(self._things_batch) > 0 or len(self._actions_batch) > 0 or len(self._reference_batch) > 0:
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