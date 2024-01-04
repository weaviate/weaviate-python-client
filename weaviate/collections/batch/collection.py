from typing import Generic, Optional, Sequence

from weaviate.collections.batch.base import _BatchBase
from weaviate.collections.batch.batch_wrapper import _BatchWrapper
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.internal import WeaviateReferences, WeaviateReference
from weaviate.collections.classes.types import Properties
from weaviate.connect import Connection
from weaviate.types import UUID


class _BatchCollection(Generic[Properties], _BatchBase):
    def __init__(
        self,
        connection: Connection,
        consistency_level: Optional[ConsistencyLevel],
        fixed_batch_size: Optional[int],
        fixed_concurrent_requests: Optional[int],
        name: str,
        tenant: Optional[str] = None,
    ) -> None:
        super().__init__(connection, consistency_level, fixed_batch_size, fixed_concurrent_requests)
        self.__name = name
        self.__tenant = tenant

    def add_object(
        self,
        properties: Optional[Properties] = None,
        references: Optional[WeaviateReferences] = None,
        uuid: Optional[UUID] = None,
        vector: Optional[Sequence] = None,
    ) -> UUID:
        """
        Add one object to this batch.

        NOTE: If the UUID of one of the objects already exists then the existing object will be replaced by the new object.

        Arguments:
            `properties`
                The data properties of the object to be added as a dictionary.
            `references`
                The references of the object to be added as a dictionary. Use `wvc.Reference.to` to create the correct values in the dict.
            `uuid`:
                The UUID of the object as an uuid.UUID object or str. It can be a Weaviate beacon or Weaviate href.
                If it is None an UUIDv4 will generated, by default None
            `vector`:
                The embedding of the object that should be validated. Can be used when a collection does not have a vectorization module or the given vector was generated using the _identical_ vectorization module that is configured for the class. In this case this vector takes precedence. Supported types are `list`, 'numpy.ndarray`, `torch.Tensor` and `tf.Tensor`, by default None.

        Returns:
            `str`
                The UUID of the added object. If one was not provided a UUIDv4 will be auto-generated for you and returned here.

        Raises:
            `WeaviateBatchValidationError`
                If the provided options are in the format required by Weaviate.
        """
        return self._add_object(
            collection=self.__name,
            properties=properties,
            references=references,
            uuid=uuid,
            vector=vector,
            tenant=self.__tenant,
        )

    def add_reference(self, from_uuid: UUID, from_property: str, to: WeaviateReference) -> None:
        """
        Add one reference to this batch.

        Arguments:
            `from_uuid`
                The UUID of the object, as an uuid.UUID object or str, that should reference another object.
                It can be a Weaviate beacon or Weaviate href.
            `from_property`
                The name of the property that contains the reference.
            `to`
                The reference to add, REQUIRED. Use `wvc.Reference.to` to create the correct value.

        Raises:
            `WeaviateBatchValidationError`
                If the provided options are in the format required by Weaviate.
        """
        for uuid in to.uuids_str:
            self._add_reference(
                from_uuid,
                self.__name,
                from_property,
                uuid,
                to.target_collection if to.is_multi_target else None,
                self.__tenant,
            )


class _BatchCollectionWrapper(Generic[Properties], _BatchWrapper):
    def __init__(
        self,
        connection: Connection,
        consistency_level: Optional[ConsistencyLevel],
        name: str,
        tenant: Optional[str] = None,
    ) -> None:
        super().__init__(connection, consistency_level)
        self.__name = name
        self.__tenant = tenant

    def __enter__(self) -> _BatchCollection[Properties]:
        self._current_batch = _BatchCollection[Properties](
            connection=self._connection,
            consistency_level=self._consistency_level,
            fixed_batch_size=self._batch_size,
            fixed_concurrent_requests=self._concurrent_requests,
            name=self.__name,
            tenant=self.__tenant,
        )
        return self._current_batch

    def configure_fixed_size(
        self,
        batch_size: int = 100,
        concurrent_requests: int = 2,
        # retry_failed_objects: bool = False,  # disable temporarily for causing endless loops
        # retry_failed_references: bool = False,
    ) -> None:
        """
        Configure your batch manager for fixed size batches. Note that the default is dynamic batching.

        When you exit the context manager, the final batch will be sent automatically.

        Arguments:
            `batch_size`
                The number of objects/references to be sent in one batch. If not provided, the default value is 100.
            `concurrent_requests`
                The number of concurrent requests when sending batches. This controls the number of concurrent requests
                made to Weaviate and not the speed of batch creation within Python.
            `retry_failed_objects`
                Whether to retry failed objects or not. If not provided, the default value is False.
            `retry_failed_references`
                Whether to retry failed references or not. If not provided, the default value is False.
        """
        self._batch_size = batch_size
        self._concurrent_requests = concurrent_requests
