import time
from requests.exceptions import ReadTimeout, Timeout
from weaviate.exceptions import UnexpectedStatusCodeException, RequestsConnectionError


class SubmitBatchesException(Exception):
    def __init__(self, message):
        super().__init__(message)


class SubmitBatches:

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

    def submit_update(self, create_func, data) -> None:
        """

        :param create_func: the function that should be called with the data
        :param data: the data that should be used as parameter to the create_func
        :return:
        :raises:
            SubmitBatchesException if the batch could not be submitted
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

    def _submit_data(self, create_func, data):
        """ Submits data using the create func and appends the result to the result collection

        :param create_func: callback function
        :param data: parameter for callback function
        :return: False if failed, True if successful
        """
        try:
            result = create_func(data)
        except (RequestsConnectionError, Timeout, ReadTimeout, UnexpectedStatusCodeException) as e:
            print("Exception in creating data: ", e)
            return False
        else:
            if isinstance(result, list):
                self._result_collection += result
                self._print_errors(result)
            return True

    def _sleep_backoff(self):
        """ Calculates an exponential backoff and sleeps for the calculated time.
            Is limited by the max_backoff_time settable in the constructor
        :return:
        """
        self._backoff_time = self._backoff_time + self._backoff_count * self._backoff_time
        if self._backoff_time > self._max_backoff_time:
            self._backoff_time = self._max_backoff_time
        else:
            self._backoff_count += 1
        time.sleep(self._backoff_time)

    def _reset_backoff(self):
        self._backoff_time = 10
        self._backoff_count = 0

    def _print_errors(self, request_result):
        if not self._verbose_enabled:
            return

        for item in request_result:
            if len(item['result']) > 0:
                if not 'status' in item['result']:
                    print(item)
                    return

                if item['result']['status'] != 'SUCCESS':
                    print(item)
