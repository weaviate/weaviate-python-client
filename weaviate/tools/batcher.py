import weaviate
import time
from requests.exceptions import ReadTimeout, Timeout, ConnectionError


class Batcher:
    """ manages batches and batch loading
    """

    def __init__(self, client, batch_size=512, print_errors=False):
        """

        :param client: weaviate client
        :type client: weaviate.Client
        :param batch_size: The batch size determines when a batch is send to weaviate.
        :type batch_size: int
        :param print_errors: if true the return status of the batches get printed
        :type print_errors: bool
        """

        self._client = client
        self._things_batch = weaviate.batch.ThingsBatchRequest()
        self._reference_batch = weaviate.batch.ReferenceBatchRequest()
        self._batch_size = batch_size
        self._print_errors_activated = print_errors

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
        if len(self._things_batch) > 0:
            try:
                result = self._client.create_things_in_batch(self._things_batch)

            except (ConnectionError, Timeout, ReadTimeout, weaviate.UnexpectedStatusCodeException) as e:
                time.sleep(180.0)
                print("Exception in adding thing: ", e)
                return
            self._print_errors(result)
            self._things_batch = weaviate.batch.ThingsBatchRequest()
        if len(self._reference_batch) > 0:
            try:
                result = self._client.add_references_in_batch(self._reference_batch)
            except (ConnectionError, Timeout, ReadTimeout, weaviate.UnexpectedStatusCodeException) as e:
                # The connection error might just be a temporary thing lets sleep and return
                # The loading will be tried again next time something is added
                # Sleep for three minutes
                time.sleep(180.0)
                print("Exception in adding reference: ", e)
                return
            self._print_errors(result)
            self._reference_batch = weaviate.batch.ReferenceBatchRequest()

    def _update_batch_if_necessary(self):
        """ Starts a batch load if the batch size is reached
        """
        if len(self._things_batch) >= self._batch_size or len(self._reference_batch) >= self._batch_size:
            self.update_batches()

    def add_thing(self, thing, class_name, thing_uuid=None):
        self._things_batch.add_thing(thing, class_name, thing_uuid)
        self._update_batch_if_necessary()

    def add_reference(self, from_thing_class_name, from_thing_uuid, from_property_name, to_thing_uuid):
        self._reference_batch.add_reference(from_thing_class_name=from_thing_class_name,
                                            from_thing_uuid=from_thing_uuid,
                                            from_property_name=from_property_name,
                                            to_thing_uuid=to_thing_uuid)
        self._update_batch_if_necessary()

    def close(self):
        """ Closes this Batcher.
            Makes sure that all unfinished batches are loaded into weaviate.
            Batcher is not useable after closing.
        """
        retry_counter = 0
        while len(self._things_batch) > 0 or len(self._reference_batch) > 0:
            # update batches might have an connection error just retry until it is successful
            self.update_batches()
            retry_counter += 1
            if retry_counter > 500:
                print("CRITICAL ERROR things can not be updated exit after 500 retries")
                exit(5)

        self._reference_batch = None
        self._things_batch = None
        self._client = None

    def __exit__(self, exception_type, exception_value, traceback):
        try:
            self.close()
        except Exception as e:
            print(e)
