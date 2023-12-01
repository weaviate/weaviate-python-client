from concurrent.futures import ThreadPoolExecutor


class BatchExecutor(ThreadPoolExecutor):
    """
    Weaviate Batch Executor to run batch requests in separate threads.

    This class implements an additional method `_is_shutdown` that is used by the context manager.
    """

    def _is_shutdown(self) -> bool:
        return self._shutdown
