from typing import List, Optional, Sequence, Union

from weaviate.collections.batch.base import _BatchBase
from weaviate.collections.batch.batch_wrapper import _BatchWrapper
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.internal import WeaviateReference
from weaviate.collections.classes.tenants import Tenant
from weaviate.collections.classes.types import WeaviateProperties
from weaviate.types import UUID


class _BatchClient(_BatchBase):
    def add_object(
        self,
        collection: str,
        properties: Optional[WeaviateProperties] = None,
        uuid: Optional[UUID] = None,
        vector: Optional[Sequence] = None,
        tenant: Optional[Union[str, Tenant]] = None,
    ) -> UUID:
        """
        Add one object to this batch.

        NOTE: If the UUID of one of the objects already exists then the existing object will be
        replaced by the new object.

        Arguments:
            `collection`
                The name of the collection this object belongs to.
            `properties`
                The data properties of the object to be added as a dictionary.
            `uuid`:
                The UUID of the object as an uuid.UUID object or str. It can be a Weaviate beacon or Weaviate href.
                If it is None an UUIDv4 will generated, by default None
            `vector`:
                The embedding of the object that should be validated. Can be used when a collection does not have a vectorization module or the given vector was generated using the _identical_ vectorization module that is configured for the class. In this case this vector takes precedence. Supported types are `list`, 'numpy.ndarray`, `torch.Tensor` and `tf.Tensor`, by default None.
            `tenant`
                Name of the tenant.

        Returns:
            `str`
                The UUID of the added object. If one was not provided a UUIDv4 will be auto-generated for you and returned here.

        Raises:
            `WeaviateBatchValidationError`
                If the provided options are in the format required by Weaviate.
        """
        return super()._add_object(
            collection=collection,
            properties=properties,
            references=None,
            uuid=uuid,
            vector=vector,
            tenant=tenant.name if isinstance(tenant, Tenant) else tenant,
        )

    def add_reference(
        self,
        from_uuid: UUID,
        from_collection: str,
        from_property: str,
        to: Union[WeaviateReference, List[UUID]],
        tenant: Optional[str] = None,
    ) -> None:
        """Add one reference to this batch.

        Arguments:
            `from_uuid`
                The UUID of the object, as an uuid.UUID object or str, that should reference another object.
            `from_collection`
                The name of the collection that should reference another object.
            `from_property`
                The name of the property that contains the reference.
            `to`
                The UUID of the referenced object, as an uuid.UUID object or str, that is actually referenced.
                For multi-target references use wvc.Reference.to_multi_targer().
            `tenant`
                Name of the tenant.

        Raises:
            `WeaviateBatchValidationError`
                If the provided options are in the format required by Weaviate.
        """
        super()._add_reference(
            from_object_uuid=from_uuid,
            from_object_collection=from_collection,
            from_property_name=from_property,
            to=to,
            tenant=tenant,
        )


class _BatchClientWrapper(_BatchWrapper):
    def __enter__(self) -> _BatchClient:
        self._open_async_connection()

        self._current_batch = _BatchClient(
            connection=self._connection,
            consistency_level=self._consistency_level,
            results=self._batch_data,
            fixed_batch_size=self._batch_size,
            fixed_concurrent_requests=self._concurrent_requests,
        )
        return self._current_batch

    def configure(self, consistency_level: Optional[ConsistencyLevel] = None) -> None:
        """Configure dynamic batching.

        Arguments:
            `consistency_level`
                The consistency level to be used to send batches. If not provided, the default value is `None`.
        """
        self._consistency_level = consistency_level

    def configure_fixed_size(
        self,
        batch_size: int = 100,
        concurrent_requests: int = 2,
        consistency_level: Optional[ConsistencyLevel] = None,
    ) -> None:
        """Configure fixed size batches. Note that the default is dynamic batching.

        Arguments:
            `batch_size`
                The number of objects/references to be sent in one batch. If not provided, the default value is 100.
            `consistency_level`
                The consistency level to be used to send the batch. If not provided, the default value is `None`.
            `concurrent_requests`
                The number of concurrent requests when sending batches. This controls the number of concurrent requests
                made to Weaviate and not the speed of batch creation within Python.
        """
        self._batch_size = batch_size
        self._consistency_level = consistency_level
        self._concurrent_requests = concurrent_requests
