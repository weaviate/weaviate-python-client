import time
from typing import Callable
from requests.exceptions import ReadTimeout, Timeout
from weaviate.exceptions import UnexpectedStatusCodeException, RequestsConnectionError
from weaviate.batch.requests import BatchRequest


class SubmitBatchesException(Exception):
    """
    Submit Batch Exception.
    """


class SubmitBatches:
    """
    SubmitBatcher class used to submit data in batcher from the Batcher object.
    """

    def __init__(self,
            max_backoff_time: int = 300,
            max_request_retries: int = 4,
            verbose_enabled: bool = False
        ):
        """
        Initialize a SubmitBatches class instance.

        Parameters
        ----------
        max_backoff_time : int, optional
            Max time used in the exponential backoff, by default 300.
        max_request_retries : int, optional
            States how often a request is retried before it counts as failed, by default 4.
        verbose_enabled : bool, optional
            If True errors will be printed directly to stdout, by default False.
        """

        self._backoff_time = 10
        self._backoff_count = 0
        self._max_backoff_time = max_backoff_time
        self._result_collection = []
        self._verbose_enabled = verbose_enabled
        self._max_request_retries = max_request_retries

    def pop_results(self) -> list:
        """
        Pops the results of the submissions.

        Returns
        -------
        list
            The results from all submitted updates since the last pop.
        """

        return_value = self._result_collection
        self._result_collection = []
        return return_value

    def submit_update(self, create_func: Callable[[BatchRequest], None], data: BatchRequest):
        """
        Parameters
        ----------
        create_func: Callable[[BatchRequest], None]
            The function that should be called with the data.
        data: BatchRequest
            The Batch object that should be used as parameter to the `create_func`.

        Raises
        ------
        SubmitBatchesException
            If the batch could not be submitted.
        """

        if len(data) == 0:
            return

        retry_counter = 0
        while not self._submit_data(create_func, data):
            self._sleep_backoff()
            retry_counter += 1
            if retry_counter >= self._max_request_retries:
                raise SubmitBatchesException("Could not submit data")

        self._reset_backoff()

    def _submit_data(self, create_func: Callable[[BatchRequest], None], data: BatchRequest):
        """
        Submits `data` using the `create_func` and appends the result to the result collection.

        Parameters
        ----------
        create_func: Callable[[BatchRequest], None]
            The function that should be called with the data.
        data: BatchRequest
            The Batch object that should be used as parameter to the `create_func`.

        Return
        bool
            False if failed, True if successful.
        """

        try:
            result = create_func(data)
        except (RequestsConnectionError, Timeout, ReadTimeout,\
                        UnexpectedStatusCodeException) as error:
            print("Exception in creating data: ", error)
            return False
        else:
            if isinstance(result, list):
                self._result_collection += result
                self._print_errors(result)
            return True

    def _sleep_backoff(self):
        """
        Calculates an exponential backoff and sleeps for the calculated time.
        Is limited by the max_backoff_time settable in the constructor
        """

        self._backoff_time = self._backoff_time + self._backoff_count * self._backoff_time
        if self._backoff_time > self._max_backoff_time:
            self._backoff_time = self._max_backoff_time
        else:
            self._backoff_count += 1
        time.sleep(self._backoff_time)

    def _reset_backoff(self):
        """
        Reset backoff values.
        """

        self._backoff_time = 10
        self._backoff_count = 0

    def _print_errors(self, request_result: dict):
        """
        Print request results, only for verbose option of the Batcher class.

        Parameters
        ----------
        request_result : dict
            Request result of the batch submission.
        """

        if not self._verbose_enabled:
            return

        for item in request_result:
            if len(item['result']) > 0:
                if not 'status' in item['result']:
                    print(item)
                    return

                if item['result']['status'] != 'SUCCESS':
                    print(item)
