import asyncio
import time
from typing import Generic, List, Optional, Any, TypeVar, cast

from weaviate.collections.batch.base import (
    _BatchBase,
    _BatchDataWrapper,
    _DynamicBatching,
    _BatchMode,
)
from weaviate.collections.classes.batch import BatchResult, ErrorObject, ErrorReference, Shard
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.connect import ConnectionV4
from weaviate.event_loop import _EventLoopSingleton
from weaviate.logger import logger
from weaviate.util import _capitalize_first_letter, _decode_json_response_list


class _BatchWrapper:
    def __init__(
        self,
        connection: ConnectionV4,
        consistency_level: Optional[ConsistencyLevel],
    ):
        self._connection = connection
        self._consistency_level = consistency_level
        self._current_batch: Optional[_BatchBase] = None
        # config options
        self._batch_mode: _BatchMode = _DynamicBatching()

        self._batch_data = _BatchDataWrapper()

        self._event_loop = _EventLoopSingleton.get_instance()

    def wait_for_vector_indexing(
        self, shards: Optional[List[Shard]] = None, how_many_failures: int = 5
    ) -> None:
        """Wait for the all the vectors of the batch imported objects to be indexed.

        Upon network error, it will retry to get the shards' status for `how_many_failures` times
        with exponential backoff (2**n seconds with n=0,1,2,...,how_many_failures).

        Arguments:
            `shards`
                The shards to check the status of. If `None` it will
                check the status of all the shards of the imported objects in the batch.
            `how_many_failures`
                How many times to try to get the shards' status before
                raising an exception. Default 5.
        """
        if shards is not None and not isinstance(shards, list):
            raise TypeError(f"'shards' must be of type List[Shard]. Given type: {type(shards)}.")
        if shards is not None and not isinstance(shards[0], Shard):
            raise TypeError(f"'shards' must be of type List[Shard]. Given type: {type(shards)}.")

        async def is_ready(how_many: int) -> bool:
            try:
                readinesses = await asyncio.gather(
                    *[
                        self.__get_shards_readiness(shard)
                        for shard in shards or self._batch_data.imported_shards
                    ]
                )
                return all(all(readiness) for readiness in readinesses)
            except Exception as e:
                logger.warning(
                    f"Error while getting class shards statuses: {e}, trying again with 2**n={2**how_many}s exponential backoff with n={how_many}"
                )
                if how_many_failures == how_many:
                    raise e
                time.sleep(2**how_many)
                return await is_ready(how_many + 1)

        count = 0
        while not self._event_loop.run_until_complete(is_ready, count):
            if count % 20 == 0:  # print every 5s
                logger.debug("Waiting for async indexing to finish...")
            time.sleep(0.25)
            count += 1
        logger.debug("Async indexing finished!")

    async def __get_shards_readiness(self, shard: Shard) -> List[bool]:
        path = f"/schema/{_capitalize_first_letter(shard.collection)}/shards{'' if shard.tenant is None else f'?tenant={shard.tenant}'}"
        response = await self._connection.get(path=path)

        res = _decode_json_response_list(response, "Get shards' status")
        assert res is not None
        return [
            (cast(str, shard.get("status")) == "READY")
            & (cast(int, shard.get("vectorQueueSize")) == 0)
            for shard in res
        ]

    def _get_shards_readiness(self, shard: Shard) -> List[bool]:
        return self._event_loop.run_until_complete(self.__get_shards_readiness, shard)

    @property
    def failed_objects(self) -> List[ErrorObject]:
        """Get all failed objects from the batch manager.

        Returns:
            `List[ErrorObject]`
                A list of all the failed objects from the batch.
        """
        return self._batch_data.failed_objects

    @property
    def failed_references(self) -> List[ErrorReference]:
        """Get all failed references from the batch manager.

        Returns:
            `List[ErrorReference]`
                A list of all the failed references from the batch.
        """
        return self._batch_data.failed_references

    @property
    def results(self) -> BatchResult:
        """Get the results of the batch operation.

        Returns:
            `BatchResult`
                The results of the batch operation.
        """
        return self._batch_data.results


T = TypeVar("T", bound=_BatchBase)


class _ContextManagerWrapper(Generic[T]):
    def __init__(self, current_batch: T):
        self.__current_batch: T = current_batch

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.__current_batch._shutdown()

    def __enter__(self) -> T:
        return self.__current_batch
