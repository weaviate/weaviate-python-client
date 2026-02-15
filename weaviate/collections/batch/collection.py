from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Generic, List, Optional, Type, Union

from deprecation import deprecated as docstring_deprecated
from typing_extensions import deprecated as typing_deprecated

from weaviate.collections.batch.async_ import _BatchBaseAsync
from weaviate.collections.batch.base import (
    _BatchBase,
    _BatchDataWrapper,
    _BatchMode,
    _DynamicBatching,
    _FixedSizeBatching,
    _RateLimitedBatching,
    _ServerSideBatching,
)
from weaviate.collections.batch.batch_wrapper import (
    BatchCollectionProtocol,
    BatchCollectionProtocolAsync,
    _BatchWrapper,
    _BatchWrapperAsync,
    _ContextManagerAsync,
    _ContextManagerSync,
)
from weaviate.collections.batch.sync import _BatchBaseSync
from weaviate.collections.classes.config import ConsistencyLevel, Vectorizers
from weaviate.collections.classes.internal import ReferenceInput, ReferenceInputs
from weaviate.collections.classes.types import Properties
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync
from weaviate.exceptions import UnexpectedStatusCodeError, WeaviateUnsupportedFeatureError
from weaviate.types import UUID, VECTORS

if TYPE_CHECKING:
    from weaviate.collections.config import _ConfigCollection


class _BatchCollection(Generic[Properties], _BatchBase):
    def __init__(
        self,
        executor: ThreadPoolExecutor,
        connection: ConnectionSync,
        consistency_level: Optional[ConsistencyLevel],
        results: _BatchDataWrapper,
        batch_mode: _BatchMode,
        name: str,
        tenant: Optional[str],
        vectorizer_batching: bool,
    ) -> None:
        super().__init__(
            connection=connection,
            consistency_level=consistency_level,
            results=results,
            batch_mode=batch_mode,
            executor=executor,
            vectorizer_batching=vectorizer_batching,
        )
        self.__name = name
        self.__tenant = tenant

    def add_object(
        self,
        properties: Optional[Properties] = None,
        references: Optional[ReferenceInputs] = None,
        uuid: Optional[UUID] = None,
        vector: Optional[VECTORS] = None,
    ) -> UUID:
        return self._add_object(
            collection=self.__name,
            properties=properties,
            references=references,
            uuid=uuid,
            vector=vector,
            tenant=self.__tenant,
        )

    def add_reference(
        self, from_uuid: UUID, from_property: str, to: Union[ReferenceInput, List[UUID]]
    ) -> None:
        self._add_reference(
            from_uuid,
            self.__name,
            from_property,
            to,
            self.__tenant,
        )


class _BatchCollectionSync(Generic[Properties], _BatchBaseSync):
    def __init__(
        self,
        connection: ConnectionSync,
        consistency_level: Optional[ConsistencyLevel],
        results: _BatchDataWrapper,
        name: str,
        tenant: Optional[str],
        executor: Optional[ThreadPoolExecutor] = None,
        batch_mode: Optional[_BatchMode] = None,
        vectorizer_batching: bool = False,
    ) -> None:
        super().__init__(
            connection=connection,
            consistency_level=consistency_level,
            results=results,
            batch_mode=batch_mode,
            executor=executor,
            vectorizer_batching=vectorizer_batching,
        )
        self.__name = name
        self.__tenant = tenant

    def add_object(
        self,
        properties: Optional[Properties] = None,
        references: Optional[ReferenceInputs] = None,
        uuid: Optional[UUID] = None,
        vector: Optional[VECTORS] = None,
    ) -> UUID:
        return self._add_object(
            collection=self.__name,
            properties=properties,
            references=references,
            uuid=uuid,
            vector=vector,
            tenant=self.__tenant,
        )

    def add_reference(
        self, from_uuid: UUID, from_property: str, to: Union[ReferenceInput, List[UUID]]
    ) -> None:
        self._add_reference(
            from_uuid,
            self.__name,
            from_property,
            to,
            self.__tenant,
        )


class _BatchCollectionAsync(Generic[Properties], _BatchBaseAsync):
    def __init__(
        self,
        connection: ConnectionAsync,
        consistency_level: Optional[ConsistencyLevel],
        results: _BatchDataWrapper,
        name: str,
        tenant: Optional[str],
    ) -> None:
        super().__init__(
            connection=connection,
            consistency_level=consistency_level,
            results=results,
        )
        self.__name = name
        self.__tenant = tenant

    async def add_object(
        self,
        properties: Optional[Properties] = None,
        references: Optional[ReferenceInputs] = None,
        uuid: Optional[UUID] = None,
        vector: Optional[VECTORS] = None,
    ) -> UUID:
        return await self._add_object(
            collection=self.__name,
            properties=properties,
            references=references,
            uuid=uuid,
            vector=vector,
            tenant=self.__tenant,
        )

    async def add_reference(
        self, from_uuid: UUID, from_property: str, to: Union[ReferenceInput, List[UUID]]
    ) -> None:
        await self._add_reference(
            from_uuid,
            self.__name,
            from_property,
            to,
            self.__tenant,
        )


BatchCollection = _BatchCollection
BatchCollectionSync = _BatchCollectionSync
BatchCollectionAsync = _BatchCollectionAsync
CollectionBatchingContextManager = _ContextManagerSync[
    Union[BatchCollection[Properties], BatchCollectionSync[Properties]],
    BatchCollectionProtocol[Properties],
]
CollectionBatchingContextManagerAsync = _ContextManagerAsync[
    BatchCollectionProtocolAsync[Properties]
]


class _BatchCollectionWrapper(Generic[Properties], _BatchWrapper):
    def __init__(
        self,
        connection: ConnectionSync,
        consistency_level: Optional[ConsistencyLevel],
        name: str,
        tenant: Optional[str],
        config: "_ConfigCollection",
        batch_client: Union[
            Type[_BatchCollection[Properties]], Type[_BatchCollectionSync[Properties]]
        ],
    ) -> None:
        super().__init__(connection, consistency_level)
        self.__name = name
        self.__tenant = tenant
        self.__config = config
        self._vectorizer_batching: Optional[bool] = None
        self.__executor = ThreadPoolExecutor()
        # define one executor per client with it shared between all child batch contexts
        self.__batch_client = batch_client

    def __create_batch_and_reset(
        self,
        batch_client: Union[
            Type[_BatchCollection[Properties]], Type[_BatchCollectionSync[Properties]]
        ],
    ):
        if self._vectorizer_batching is None:
            try:
                config = self.__config.get(simple=True)
                if config.vector_config is not None:
                    vectorizer_batching = False
                    for vec_config in config.vector_config.values():
                        if vec_config.vectorizer.vectorizer is not Vectorizers.NONE:
                            vectorizer_batching = True
                            break
                    self._vectorizer_batching = vectorizer_batching
                else:
                    self._vectorizer_batching = config.vectorizer is not Vectorizers.NONE
            except UnexpectedStatusCodeError as e:
                # collection does not have to exist if autoschema is enabled. Individual objects will be validated and might fail
                if e.status_code != 404:
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
                name=self.__name,
                tenant=self.__tenant,
                vectorizer_batching=self._vectorizer_batching,
            )
        )

    def dynamic(self) -> CollectionBatchingContextManager[Properties]:
        """Configure dynamic batching.

        When you exit the context manager, the final batch will be sent automatically.
        """
        self._batch_mode: _BatchMode = _DynamicBatching()
        return self.__create_batch_and_reset(_BatchCollection)

    def fixed_size(
        self, batch_size: int = 100, concurrent_requests: int = 2
    ) -> CollectionBatchingContextManager[Properties]:
        """Configure fixed size batches. Note that the default is dynamic batching.

        When you exit the context manager, the final batch will be sent automatically.

        Args:
            batch_size: The number of objects/references to be sent in one batch. If not provided, the default value is 100.
            concurrent_requests: The number of concurrent requests when sending batches. This controls the number of concurrent requests
                made to Weaviate and not the speed of batch creation within Python.
        """
        self._batch_mode = _FixedSizeBatching(batch_size, concurrent_requests)
        return self.__create_batch_and_reset(_BatchCollection)

    def rate_limit(self, requests_per_minute: int) -> CollectionBatchingContextManager[Properties]:
        """Configure batches with a rate limited vectorizer.

        When you exit the context manager, the final batch will be sent automatically.

        Args:
            requests_per_minute: The number of requests that the vectorizer can process per minute.
        """
        self._batch_mode = _RateLimitedBatching(requests_per_minute)
        return self.__create_batch_and_reset(_BatchCollection)

    @docstring_deprecated(
        details="Use the 'stream' method instead. This method will be removed in 4.21.0",
        deprecated_in="4.20.0",
    )
    @typing_deprecated("Use the 'stream' method instead. This method will be removed in 4.21.0")
    def experimental(
        self,
        *,
        concurrency: Optional[int] = None,
    ) -> CollectionBatchingContextManager[Properties]:
        return self.stream(concurrency=concurrency)

    def stream(
        self,
        *,
        concurrency: Optional[int] = None,
    ) -> CollectionBatchingContextManager[Properties]:
        """Configure the batching context manager to use batch streaming.

        When you exit the context manager, the final batch will be sent automatically.

        Args:
            concurrency: The number of concurrent requests when sending batches. This controls the number of concurrent requests
                made to Weaviate. If not provided, the default value is 1.
        """
        if self._connection._weaviate_version.is_lower_than(1, 36, 0):
            raise WeaviateUnsupportedFeatureError(
                "Server-side batching", str(self._connection._weaviate_version), "1.36.0"
            )
        self._batch_mode = _ServerSideBatching(
            # concurrency=concurrency
            # if concurrency is not None
            # else len(self._cluster.get_nodes_status())
            concurrency=concurrency or 1,
        )
        return self.__create_batch_and_reset(_BatchCollectionSync)


class _BatchCollectionWrapperAsync(Generic[Properties], _BatchWrapperAsync):
    def __init__(
        self,
        connection: ConnectionAsync,
        consistency_level: Optional[ConsistencyLevel],
        name: str,
        tenant: Optional[str],
    ) -> None:
        super().__init__(connection, consistency_level)
        self.__name = name
        self.__tenant = tenant

    def __create_batch_and_reset(self):
        self._batch_data = _BatchDataWrapper()  # clear old data
        return _ContextManagerAsync(
            BatchCollectionAsync(
                connection=self._connection,
                consistency_level=self._consistency_level,
                results=self._batch_data,
                name=self.__name,
                tenant=self.__tenant,
            )
        )

    @docstring_deprecated(
        details="Use the 'stream' method instead. This method will be removed in 4.21.0",
        deprecated_in="4.20.0",
    )
    @typing_deprecated("Use the 'stream' method instead. This method will be removed in 4.21.0")
    def experimental(
        self,
    ) -> CollectionBatchingContextManagerAsync[Properties]:
        return self.stream()

    def stream(
        self,
        *,
        concurrency: Optional[int] = None,
    ) -> CollectionBatchingContextManagerAsync[Properties]:
        """Configure the batching context manager to use batch streaming.

        When you exit the context manager, the final batch will be sent automatically.

        Args:
            concurrency: The number of concurrent requests when sending batches. This controls the number of concurrent requests
                made to Weaviate. If not provided, the default value is 1.
        """
        if self._connection._weaviate_version.is_lower_than(1, 36, 0):
            raise WeaviateUnsupportedFeatureError(
                "Server-side batching", str(self._connection._weaviate_version), "1.36.0"
            )
        self._batch_mode = _ServerSideBatching(
            # concurrency=concurrency
            # if concurrency is not None
            # else len(self._cluster.get_nodes_status())
            concurrency=concurrency or 1,
        )
        return self.__create_batch_and_reset()
