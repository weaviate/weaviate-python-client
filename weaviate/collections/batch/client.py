from typing import Optional, Union

from weaviate.collections.batch.base import (
    _BatchBase,
    _BatchDataWrapper,
    _DynamicBatching,
    _FixedSizeBatching,
    _RateLimitedBatching,
)
from weaviate.collections.batch.batch_wrapper import (
    _BatchWrapper,
    _BatchMode,
    _ContextManagerWrapper,
)
from weaviate.collections.classes.config import ConsistencyLevel, Vectorizers
from weaviate.collections.classes.internal import ReferenceInput, ReferenceInputs
from weaviate.collections.classes.tenants import Tenant
from weaviate.collections.classes.types import WeaviateProperties
from weaviate.exceptions import UnexpectedStatusCodeError
from weaviate.types import UUID, VECTORS

from weaviate.connect.v4 import ConnectionV4

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from weaviate.collections.collections.sync import _Collections


class _BatchClient(_BatchBase):
    def add_object(
        self,
        collection: str,
        properties: Optional[WeaviateProperties] = None,
        references: Optional[ReferenceInputs] = None,
        uuid: Optional[UUID] = None,
        vector: Optional[VECTORS] = None,
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
            `references`
                The references of the object to be added as a dictionary.
            `uuid`:
                The UUID of the object as an uuid.UUID object or str. It can be a Weaviate beacon or Weaviate href.
                If it is None an UUIDv4 will generated, by default None
            `vector`:
                The embedding of the object. Can be used when a collection does not have a vectorization module or the given
                vector was generated using the _identical_ vectorization module that is configured for the class. In this
                case this vector takes precedence.
                Supported types are
                - for single vectors: `list`, 'numpy.ndarray`, `torch.Tensor` and `tf.Tensor`, by default None.
                - for named vectors: Dict[str, *list above*], where the string is the name of the vector.
            `tenant`
                The tenant name or Tenant object to be used for this request.

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
            references=references,
            uuid=uuid,
            vector=vector,
            tenant=tenant.name if isinstance(tenant, Tenant) else tenant,
        )

    def add_reference(
        self,
        from_uuid: UUID,
        from_collection: str,
        from_property: str,
        to: ReferenceInput,
        tenant: Optional[Union[str, Tenant]] = None,
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
                For multi-target references use wvc.Reference.to_multi_target().
            `tenant`
                The tenant name or Tenant object to be used for this request.

        Raises:
            `WeaviateBatchValidationError`
                If the provided options are in the format required by Weaviate.
        """
        super()._add_reference(
            from_object_uuid=from_uuid,
            from_object_collection=from_collection,
            from_property_name=from_property,
            to=to,
            tenant=tenant.name if isinstance(tenant, Tenant) else tenant,
        )


BatchClient = _BatchClient
ClientBatchingContextManager = _ContextManagerWrapper[BatchClient]


class _BatchClientWrapper(_BatchWrapper):
    def __init__(
        self,
        connection: ConnectionV4,
        config: "_Collections",
        consistency_level: Optional[ConsistencyLevel] = None,
    ):
        super().__init__(connection, consistency_level)
        self.__config = config
        self._vectorizer_batching: Optional[bool] = None

    def __create_batch_and_reset(self) -> _ContextManagerWrapper[_BatchClient]:
        if self._vectorizer_batching is None or not self._vectorizer_batching:
            try:
                configs = self.__config.list_all(simple=True)

                vectorizer_batching = False
                for config in configs.values():
                    if config.vector_config is not None:
                        vectorizer_batching = False
                        for vec_config in config.vector_config.values():
                            if vec_config.vectorizer.vectorizer is not Vectorizers.NONE:
                                vectorizer_batching = True
                                break
                        vectorizer_batching = vectorizer_batching
                    else:
                        vectorizer_batching = any(
                            config.vectorizer_config is not None for config in configs.values()
                        )
                    if vectorizer_batching:
                        break
                self._vectorizer_batching = vectorizer_batching
            except UnexpectedStatusCodeError as e:
                # we might not have the rights to query all collections
                if e.status_code != 403:
                    raise e
                self._vectorizer_batching = False

        self._batch_data = _BatchDataWrapper()  # clear old data
        return _ContextManagerWrapper(
            _BatchClient(
                connection=self._connection,
                consistency_level=self._consistency_level,
                results=self._batch_data,
                batch_mode=self._batch_mode,
                event_loop=self._event_loop,
                vectorizer_batching=self._vectorizer_batching,
            )
        )

    def dynamic(
        self, consistency_level: Optional[ConsistencyLevel] = None
    ) -> ClientBatchingContextManager:
        """Configure dynamic batching.

        When you exit the context manager, the final batch will be sent automatically.

        Arguments:
            `consistency_level`
                The consistency level to be used to send batches. If not provided, the default value is `None`.
        """
        self._batch_mode: _BatchMode = _DynamicBatching()
        self._consistency_level = consistency_level
        return self.__create_batch_and_reset()

    def fixed_size(
        self,
        batch_size: int = 100,
        concurrent_requests: int = 2,
        consistency_level: Optional[ConsistencyLevel] = None,
    ) -> _ContextManagerWrapper[_BatchClient]:
        """Configure fixed size batches. Note that the default is dynamic batching.

        When you exit the context manager, the final batch will be sent automatically.

        Arguments:
            `batch_size`
                The number of objects/references to be sent in one batch. If not provided, the default value is 100.
            `concurrent_requests`
                The number of concurrent requests when sending batches. This controls the number of concurrent requests
                made to Weaviate and not the speed of batch creation within Python.
            `consistency_level`
                The consistency level to be used to send batches. If not provided, the default value is `None`.

        """
        self._batch_mode = _FixedSizeBatching(batch_size, concurrent_requests)
        self._consistency_level = consistency_level
        return self.__create_batch_and_reset()

    def rate_limit(
        self, requests_per_minute: int, consistency_level: Optional[ConsistencyLevel] = None
    ) -> ClientBatchingContextManager:
        """Configure batches with a rate limited vectorizer.

        When you exit the context manager, the final batch will be sent automatically.

        Arguments:
            `requests_per_minute`
                The number of requests that the vectorizer can process per minute.
            `consistency_level`
                The consistency level to be used to send batches. If not provided, the default value is `None`.
        """
        self._batch_mode = _RateLimitedBatching(requests_per_minute)
        self._consistency_level = consistency_level
        return self.__create_batch_and_reset()
