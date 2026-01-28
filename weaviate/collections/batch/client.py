from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Optional, Type, Union

from weaviate.collections.batch.async_ import _BatchBaseAsync
from weaviate.collections.batch.base import (
    _BatchBase,
    _BatchDataWrapper,
    _DynamicBatching,
    _FixedSizeBatching,
    _RateLimitedBatching,
    _ServerSideBatching,
)
from weaviate.collections.batch.batch_wrapper import (
    BatchClientProtocol,
    BatchClientProtocolAsync,
    _BatchMode,
    _BatchWrapper,
    _BatchWrapperAsync,
    _ContextManagerAsync,
    _ContextManagerSync,
)
from weaviate.collections.batch.sync import _BatchBaseSync
from weaviate.collections.classes.config import ConsistencyLevel, Vectorizers
from weaviate.collections.classes.internal import ReferenceInput, ReferenceInputs
from weaviate.collections.classes.tenants import Tenant
from weaviate.collections.classes.types import WeaviateProperties
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync
from weaviate.exceptions import UnexpectedStatusCodeError, WeaviateUnsupportedFeatureError
from weaviate.types import UUID, VECTORS

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
        super()._add_reference(
            from_object_uuid=from_uuid,
            from_object_collection=from_collection,
            from_property_name=from_property,
            to=to,
            tenant=tenant.name if isinstance(tenant, Tenant) else tenant,
        )


class _BatchClientSync(_BatchBaseSync):
    def add_object(
        self,
        collection: str,
        properties: Optional[WeaviateProperties] = None,
        references: Optional[ReferenceInputs] = None,
        uuid: Optional[UUID] = None,
        vector: Optional[VECTORS] = None,
        tenant: Optional[Union[str, Tenant]] = None,
    ) -> UUID:
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
        super()._add_reference(
            from_object_uuid=from_uuid,
            from_object_collection=from_collection,
            from_property_name=from_property,
            to=to,
            tenant=tenant.name if isinstance(tenant, Tenant) else tenant,
        )


class _BatchClientAsync(_BatchBaseAsync):
    async def add_object(
        self,
        collection: str,
        properties: Optional[WeaviateProperties] = None,
        references: Optional[ReferenceInputs] = None,
        uuid: Optional[UUID] = None,
        vector: Optional[VECTORS] = None,
        tenant: Optional[Union[str, Tenant]] = None,
    ) -> UUID:
        return await super()._add_object(
            collection=collection,
            properties=properties,
            references=references,
            uuid=uuid,
            vector=vector,
            tenant=tenant.name if isinstance(tenant, Tenant) else tenant,
        )

    async def add_reference(
        self,
        from_uuid: UUID,
        from_collection: str,
        from_property: str,
        to: ReferenceInput,
        tenant: Optional[Union[str, Tenant]] = None,
    ) -> None:
        await super()._add_reference(
            from_object_uuid=from_uuid,
            from_object_collection=from_collection,
            from_property_name=from_property,
            to=to,
            tenant=tenant.name if isinstance(tenant, Tenant) else tenant,
        )


BatchClient = _BatchClient
BatchClientSync = _BatchClientSync
BatchClientAsync = _BatchClientAsync
ClientBatchingContextManager = _ContextManagerSync[
    Union[BatchClient, BatchClientSync], BatchClientProtocol
]
ClientBatchingContextManagerAsync = _ContextManagerAsync[BatchClientProtocolAsync]


class _BatchClientWrapper(_BatchWrapper):
    def __init__(
        self,
        connection: ConnectionSync,
        config: "_Collections",
        consistency_level: Optional[ConsistencyLevel],
    ):
        super().__init__(connection, consistency_level)
        self.__config = config
        self._vectorizer_batching: Optional[bool] = None
        self.__executor = ThreadPoolExecutor()
        # define one executor per client with it shared between all child batch contexts

    def __create_batch_and_reset(
        self, batch_client: Union[Type[_BatchClient], Type[_BatchClientSync]]
    ):
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

        return _ContextManagerSync(
            batch_client(
                connection=self._connection,
                consistency_level=self._consistency_level,
                results=self._batch_data,
                batch_mode=self._batch_mode,
                executor=self.__executor,
                vectorizer_batching=self._vectorizer_batching,
            )
        )

    def dynamic(
        self, consistency_level: Optional[ConsistencyLevel] = None
    ) -> ClientBatchingContextManager:
        """Configure dynamic batching.

        When you exit the context manager, the final batch will be sent automatically.

        Args:
            consistency_level: The consistency level to be used to send batches. If not provided, the default value is `None`.
        """
        self._batch_mode: _BatchMode = _DynamicBatching()
        self._consistency_level = consistency_level
        return self.__create_batch_and_reset(_BatchClient)

    def fixed_size(
        self,
        batch_size: int = 100,
        concurrent_requests: int = 2,
        consistency_level: Optional[ConsistencyLevel] = None,
    ) -> ClientBatchingContextManager:
        """Configure fixed size batches. Note that the default is dynamic batching.

        When you exit the context manager, the final batch will be sent automatically.

        Args:
            batch_size: The number of objects/references to be sent in one batch. If not provided, the default value is 100.
            concurrent_requests: The number of concurrent requests when sending batches. This controls the number of concurrent requests
                made to Weaviate and not the speed of batch creation within Python.
            consistency_level: The consistency level to be used to send batches. If not provided, the default value is `None`.

        """
        self._batch_mode = _FixedSizeBatching(batch_size, concurrent_requests)
        self._consistency_level = consistency_level
        return self.__create_batch_and_reset(_BatchClient)

    def rate_limit(
        self,
        requests_per_minute: int,
        consistency_level: Optional[ConsistencyLevel] = None,
    ) -> ClientBatchingContextManager:
        """Configure batches with a rate limited vectorizer.

        When you exit the context manager, the final batch will be sent automatically.

        Args:
            requests_per_minute: The number of requests that the vectorizer can process per minute.
            consistency_level: The consistency level to be used to send batches. If not provided, the default value is `None`.
        """
        self._batch_mode = _RateLimitedBatching(requests_per_minute)
        self._consistency_level = consistency_level
        return self.__create_batch_and_reset(_BatchClient)

    def experimental(
        self,
        *,
        concurrency: Optional[int] = None,
        consistency_level: Optional[ConsistencyLevel] = None,
    ) -> ClientBatchingContextManager:
        """Configure the batching context manager using the experimental server-side batching mode.

        When you exit the context manager, the final batch will be sent automatically.
        """
        if self._connection._weaviate_version.is_lower_than(1, 34, 0):
            raise WeaviateUnsupportedFeatureError(
                "Server-side batching", str(self._connection._weaviate_version), "1.34.0"
            )
        self._batch_mode = _ServerSideBatching(
            # concurrency=concurrency
            # if concurrency is not None
            # else len(self._cluster.get_nodes_status())
            concurrency=1,  # hard-code until client-side multi-threading is fixed
        )
        self._consistency_level = consistency_level
        return self.__create_batch_and_reset(_BatchClientSync)


class _BatchClientWrapperAsync(_BatchWrapperAsync):
    def __init__(
        self,
        connection: ConnectionAsync,
    ):
        super().__init__(connection, None)
        self._vectorizer_batching: Optional[bool] = None

    def __create_batch_and_reset(self):
        self._batch_data = _BatchDataWrapper()  # clear old data
        return _ContextManagerAsync(
            BatchClientAsync(
                connection=self._connection,
                consistency_level=self._consistency_level,
                results=self._batch_data,
            )
        )

    def experimental(
        self,
        *,
        concurrency: Optional[int] = None,
        consistency_level: Optional[ConsistencyLevel] = None,
    ) -> ClientBatchingContextManagerAsync:
        """Configure the batching context manager using the experimental server-side batching mode.

        When you exit the context manager, the final batch will be sent automatically.
        """
        if self._connection._weaviate_version.is_lower_than(1, 34, 0):
            raise WeaviateUnsupportedFeatureError(
                "Server-side batching", str(self._connection._weaviate_version), "1.34.0"
            )
        self._batch_mode = _ServerSideBatching(
            # concurrency=concurrency
            # if concurrency is not None
            # else len(self._cluster.get_nodes_status())
            concurrency=1,  # hard-code until client-side multi-threading is fixed
        )
        self._consistency_level = consistency_level
        return self.__create_batch_and_reset()
