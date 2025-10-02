import time
from typing import Any, Generic, List, Optional, Protocol, TypeVar, Union, cast

from weaviate.collections.batch.base import (
    _BatchBase,
    _BatchBaseNew,
    _BatchDataWrapper,
    _BatchMode,
    _ClusterBatch,
    _DynamicBatching,
)
from weaviate.collections.classes.batch import (
    BatchResult,
    ErrorObject,
    ErrorReference,
    Shard,
)
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.internal import ReferenceInput, ReferenceInputs
from weaviate.collections.classes.tenants import Tenant
from weaviate.collections.classes.types import Properties, WeaviateProperties
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync
from weaviate.logger import logger
from weaviate.types import UUID, VECTORS
from weaviate.util import _capitalize_first_letter, _decode_json_response_list


class _BatchWrapper:
    def __init__(
        self,
        connection: ConnectionSync,
        consistency_level: Optional[ConsistencyLevel],
    ):
        self._connection = connection
        self._consistency_level = consistency_level
        self._current_batch: Optional[Union[_BatchBase, _BatchBaseNew]] = None
        # config options
        self._batch_mode: _BatchMode = _DynamicBatching()

        self._batch_data = _BatchDataWrapper()
        self._cluster = _ClusterBatch(connection)

    def __is_ready(
        self, max_count: int, shards: Optional[List[Shard]], backoff_count: int = 0
    ) -> bool:
        try:
            readinesses = [
                self.__get_shards_readiness(shard)
                for shard in shards or self._batch_data.imported_shards
            ]
            return all(all(readiness) for readiness in readinesses)
        except Exception as e:
            logger.warning(
                f"Error while getting class shards statuses: {e}, trying again with 2**n={2**backoff_count}s exponential backoff with n={backoff_count}"
            )
            if backoff_count >= max_count:
                raise e
            time.sleep(2**backoff_count)
            return self.__is_ready(max_count, shards, backoff_count + 1)

    def wait_for_vector_indexing(
        self, shards: Optional[List[Shard]] = None, how_many_failures: int = 5
    ) -> None:
        """Wait for the all the vectors of the batch imported objects to be indexed.

        Upon network error, it will retry to get the shards' status for `how_many_failures` times
        with exponential backoff (2**n seconds with n=0,1,2,...,how_many_failures).

        Args:
            shards: The shards to check the status of. If `None` it will check the status of all the shards of the imported objects in the batch.
            how_many_failures: How many times to try to get the shards' status before raising an exception. Default 5.
        """
        if shards is not None and not isinstance(shards, list):
            raise TypeError(f"'shards' must be of type List[Shard]. Given type: {type(shards)}.")
        if shards is not None and not isinstance(shards[0], Shard):
            raise TypeError(f"'shards' must be of type List[Shard]. Given type: {type(shards)}.")

        waiting_count = 0
        while not self.__is_ready(how_many_failures, shards):
            if waiting_count % 20 == 0:  # print every 5s
                logger.debug("Waiting for async indexing to finish...")
            time.sleep(0.25)
            waiting_count += 1
        logger.debug("Async indexing finished!")

    def __get_shards_readiness(self, shard: Shard) -> List[bool]:
        path = f"/schema/{_capitalize_first_letter(shard.collection)}/shards{'' if shard.tenant is None else f'?tenant={shard.tenant}'}"
        response = executor.result(self._connection.get(path=path))

        res = _decode_json_response_list(response, "Get shards' status")
        assert res is not None
        return [
            (cast(str, shard.get("status")) == "READY")
            & (cast(int, shard.get("vectorQueueSize")) == 0)
            for shard in res
        ]

    def _get_shards_readiness(self, shard: Shard) -> List[bool]:
        return self.__get_shards_readiness(shard)

    @property
    def failed_objects(self) -> List[ErrorObject]:
        """Get all failed objects from the batch manager.

        Returns:
            A list of all the failed objects from the batch.
        """
        return self._batch_data.failed_objects

    @property
    def failed_references(self) -> List[ErrorReference]:
        """Get all failed references from the batch manager.

        Returns:
            A list of all the failed references from the batch.
        """
        return self._batch_data.failed_references

    @property
    def results(self) -> BatchResult:
        """Get the results of the batch operation.

        Returns:
            The results of the batch operation.
        """
        return self._batch_data.results


class BatchClientProtocol(Protocol):
    def add_object(
        self,
        collection: str,
        properties: Optional[WeaviateProperties] = None,
        references: Optional[ReferenceInputs] = None,
        uuid: Optional[UUID] = None,
        vector: Optional[VECTORS] = None,
        tenant: Optional[Union[str, Tenant]] = None,
    ) -> UUID:
        """Add one object to this batch.

        NOTE: If the UUID of one of the objects already exists then the existing object will be
        replaced by the new object.

        Args:
            collection: The name of the collection this object belongs to.
            properties: The data properties of the object to be added as a dictionary.
            references: The references of the object to be added as a dictionary.
            uuid: The UUID of the object as an uuid.UUID object or str. It can be a Weaviate beacon or Weaviate href.
                If it is None an UUIDv4 will generated, by default None
            vector: The embedding of the object. Can be used when a collection does not have a vectorization module or the given
                vector was generated using the _identical_ vectorization module that is configured for the class. In this
                case this vector takes precedence.
                Supported types are:
                - for single vectors: `list`, 'numpy.ndarray`, `torch.Tensor` and `tf.Tensor`, by default None.
                - for named vectors: Dict[str, *list above*], where the string is the name of the vector.
            tenant: The tenant name or Tenant object to be used for this request.

        Returns:
            The UUID of the added object. If one was not provided a UUIDv4 will be auto-generated for you and returned here.

        Raises:
            WeaviateBatchValidationError: If the provided options are in the format required by Weaviate.
        """
        ...

    def add_reference(
        self,
        from_uuid: UUID,
        from_collection: str,
        from_property: str,
        to: ReferenceInput,
        tenant: Optional[Union[str, Tenant]] = None,
    ) -> None:
        """Add one reference to this batch.

        Args:
            from_uuid: The UUID of the object, as an uuid.UUID object or str, that should reference another object.
            from_collection: The name of the collection that should reference another object.
            from_property: The name of the property that contains the reference.
            to: The UUID of the referenced object, as an uuid.UUID object or str, that is actually referenced.
                For multi-target references use wvc.Reference.to_multi_target().
            tenant: The tenant name or Tenant object to be used for this request.

        Raises:
            WeaviateBatchValidationError: If the provided options are in the format required by Weaviate.
        """
        ...

    def flush(self) -> None:
        """Flush the current batch.

        This will send all the objects and references in the current batch to Weaviate.
        """
        ...

    @property
    def number_errors(self) -> int:
        """Get the number of errors in the current batch.

        Returns:
            The number of errors in the current batch.
        """
        ...


class BatchCollectionProtocol(Generic[Properties], Protocol[Properties]):
    def add_object(
        self,
        properties: Optional[Properties] = None,
        references: Optional[ReferenceInputs] = None,
        uuid: Optional[UUID] = None,
        vector: Optional[VECTORS] = None,
    ) -> UUID:
        """Add one object to this batch.

        NOTE: If the UUID of one of the objects already exists then the existing object will be replaced by the new object.

        Args:
            properties: The data properties of the object to be added as a dictionary.
            references: The references of the object to be added as a dictionary.
            uuid: The UUID of the object as an uuid.UUID object or str. If it is None an UUIDv4 will generated, by default None
            vector: The embedding of the object. Can be used when a collection does not have a vectorization module or the given
                vector was generated using the _identical_ vectorization module that is configured for the class. In this
                case this vector takes precedence. Supported types are:
                - for single vectors: `list`, 'numpy.ndarray`, `torch.Tensor` and `tf.Tensor`, by default None.
                - for named vectors: Dict[str, *list above*], where the string is the name of the vector.

        Returns:
            The UUID of the added object. If one was not provided a UUIDv4 will be auto-generated for you and returned here.

        Raises:
            WeaviateBatchValidationError: If the provided options are in the format required by Weaviate.
        """
        ...

    def add_reference(
        self, from_uuid: UUID, from_property: str, to: Union[ReferenceInput, List[UUID]]
    ) -> None:
        """Add a reference to this batch.

        Args:
            from_uuid: The UUID of the object, as an uuid.UUID object or str, that should reference another object.
            from_property: The name of the property that contains the reference.
            to: The UUID of the referenced object, as an uuid.UUID object or str, that is actually referenced.
                For multi-target references use wvc.Reference.to_multi_target().

        Raises:
            WeaviateBatchValidationError: If the provided options are in the format required by Weaviate.
        """
        ...

    @property
    def number_errors(self) -> int:
        """Get the number of errors in the current batch.

        Returns:
            The number of errors in the current batch.
        """
        ...


T = TypeVar("T", bound=Union[_BatchBase, _BatchBaseNew])
P = TypeVar("P", bound=Union[BatchClientProtocol, BatchCollectionProtocol[Properties]])


class _ContextManagerWrapper(Generic[T, P]):
    def __init__(self, current_batch: T):
        self.__current_batch: T = current_batch

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.__current_batch._shutdown()

    def __enter__(self) -> P:
        self.__current_batch._start()
        return self.__current_batch  # pyright: ignore[reportReturnType]
