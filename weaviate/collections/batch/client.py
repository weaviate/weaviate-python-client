from typing import Optional, Sequence, Union

from weaviate.collections.batch.base import _BatchBase
from weaviate.collections.batch.batch_wrapper import _BatchWrapper
from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.tenants import Tenant
from weaviate.collections.classes.types import WeaviateProperties
from weaviate.connect import Connection
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
        from_object_uuid: UUID,
        from_object_collection: str,
        from_property_name: str,
        to_object_uuid: UUID,
        to_object_collection: Optional[str] = None,
        tenant: Optional[str] = None,
    ) -> None:
        """
        Add one reference to this batch.

        Arguments:
            `from_object_uuid`
                The UUID of the object, as an uuid.UUID object or str, that should reference another object.
                It can be a Weaviate beacon or Weaviate href.
            `from_object_collection`
                The name of the collection that should reference another object.
            `from_property_name`
                The name of the property that contains the reference.
            `to_object_uuid`
                The UUID of the object, as an uuid.UUID object or str, that is actually referenced.
                It can be a Weaviate beacon or Weaviate href.
            `to_object_collection`
                The referenced object collection to which to add the reference (with UUID `to_object_uuid`).
            `tenant`
                Name of the tenant.

        Raises:
            `WeaviateBatchValidationError`
                If the provided options are in the format required by Weaviate.
        """
        super()._add_reference(
            from_object_uuid=from_object_uuid,
            from_object_collection=from_object_collection,
            from_property_name=from_property_name,
            to_object_uuid=to_object_uuid,
            to_object_collection=to_object_collection,
            tenant=tenant,
        )


class _BatchClientWrapper(_BatchWrapper):
    def __init__(self, connection: Connection) -> None:
        super().__init__(connection, None)

    def __enter__(self) -> _BatchClient:
        self._current_batch = _BatchClient(
            connection=self._connection,
            consistency_level=self._consistency_level,
            fixed_batch_size=self._batch_size,
            fixed_concurrent_requests=self._concurrent_requests,
        )
        return self._current_batch

    def configure(
        self,
        consistency_level: Optional[ConsistencyLevel] = None,
        # retry_failed_objects: bool = False,  # disable temporarily for causing endless loops
        # retry_failed_references: bool = False,
    ) -> None:
        """Configure dynamic batching.

        Arguments:
            `consistency_level`
                The consistency level to be used to send the batch. If not provided, the default value is `None`.
        """
        self._consistency_level = consistency_level

    def configure_fixed_size(
        self,
        batch_size: int = 100,
        concurrent_requests: int = 2,
        consistency_level: Optional[ConsistencyLevel] = None,
        # retry_failed_objects: bool = False,  # disable temporarly for causing endless loops
        # retry_failed_references: bool = False,
    ) -> None:
        """
        Configure your batch manager.

        Every time you run this command, the `client.batch` object will
        be updated with the new configuration. To enter the batching context manager, which handles automatically
        sending batches dynamically, use `with client.batch as batch` and then loop through your data within the context manager
        adding objects and references to the batch.

        Batches are constructed automatically and sent dynamically depending on Weaviate's load.
        When you exit the context manager, the final batch will be sent automatically.

        Arguments:
            `batch_size`
                The number of objects/references to be sent in one batch. If not provided, the default value is 100.
            `consistency_level`
                The consistency level to be used to send the batch. If not provided, the default value is `None`.
            `concurrent_requests`
                The number of workers to be used when sending the batches. If not provided, the default value is `None` which uses the Python defined
                default value of `min(32, (os.cpu_count() or 1) + 4)`.
                This controls the number of concurrent requests made to Weaviate and not the speed of batch creation within Python.
            `retry_failed_objects`
                Whether to retry failed objects or not. If not provided, the default value is False.
            `retry_failed_references`
                Whether to retry failed references or not. If not provided, the default value is False.
        """
        self._batch_size = batch_size
        self._consistency_level = consistency_level
        self._concurrent_requests = concurrent_requests
        # self.__retry_failed_objects = retry_failed_objects
        # self.__retry_failed_references = retry_failed_references
