import os
from typing import (
    Any,
    AsyncGenerator,
    Optional,
    List,
    Generator,
    Protocol,
    Type,
    Dict,
    Tuple,
    Union,
)

import pytest
import pytest_asyncio
from _pytest.fixtures import SubRequest

import weaviate
from weaviate.collections import Collection, CollectionAsync
from weaviate.collections.classes.config import (
    Property,
    _VectorizerConfigCreate,
    _InvertedIndexConfigCreate,
    _ReferencePropertyBase,
    Configure,
    _GenerativeProvider,
    _ReplicationConfigCreate,
    DataType,
    _MultiTenancyConfigCreate,
    _VectorIndexConfigCreate,
    _RerankerProvider,
)
from weaviate.collections.classes.config_named_vectors import _NamedVectorConfigCreate
from weaviate.collections.classes.types import Properties
from weaviate.config import AdditionalConfig


class CollectionFactory(Protocol):
    """Typing for fixture."""

    def __call__(
        self,
        name: str = "",
        properties: Optional[List[Property]] = None,
        references: Optional[List[_ReferencePropertyBase]] = None,
        vectorizer_config: Optional[
            Union[_VectorizerConfigCreate, List[_NamedVectorConfigCreate]]
        ] = None,
        inverted_index_config: Optional[_InvertedIndexConfigCreate] = None,
        multi_tenancy_config: Optional[_MultiTenancyConfigCreate] = None,
        generative_config: Optional[_GenerativeProvider] = None,
        headers: Optional[Dict[str, str]] = None,
        ports: Tuple[int, int] = (8080, 50051),
        data_model_properties: Optional[Type[Properties]] = None,
        data_model_refs: Optional[Type[Properties]] = None,
        replication_config: Optional[_ReplicationConfigCreate] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        description: Optional[str] = None,
        reranker_config: Optional[_RerankerProvider] = None,
    ) -> Collection[Any, Any]:
        """Typing for fixture."""
        ...


class ClientFactory(Protocol):
    """Typing for fixture."""

    def __call__(
        self,
        headers: Optional[Dict[str, str]] = None,
        ports: Tuple[int, int] = (8080, 50051),
    ) -> weaviate.WeaviateClient:
        """Typing for fixture."""
        ...


@pytest.fixture
def client_factory() -> Generator[ClientFactory, None, None]:
    client_fixture: Optional[weaviate.WeaviateClient] = None

    def _factory(
        headers: Optional[Dict[str, str]] = None,
        ports: Tuple[int, int] = (8080, 50051),
    ) -> weaviate.WeaviateClient:
        nonlocal client_fixture
        if client_fixture is None:
            client_fixture = weaviate.connect_to_local(
                headers=headers,
                grpc_port=ports[1],
                port=ports[0],
                additional_config=AdditionalConfig(timeout=(60, 120)),  # for image tests
            )
        return client_fixture

    try:
        yield _factory
    finally:
        if client_fixture is not None:
            client_fixture.close()


@pytest.fixture
def collection_factory(
    request: SubRequest, client_factory: ClientFactory
) -> Generator[CollectionFactory, None, None]:
    name_fixtures: List[str] = []
    client_fixture: Optional[weaviate.WeaviateClient] = None
    call_counter: int = 0

    def _factory(
        name: str = "",
        properties: Optional[List[Property]] = None,
        references: Optional[List[_ReferencePropertyBase]] = None,
        vectorizer_config: Optional[
            Union[_VectorizerConfigCreate, List[_NamedVectorConfigCreate]]
        ] = None,
        inverted_index_config: Optional[_InvertedIndexConfigCreate] = None,
        multi_tenancy_config: Optional[_MultiTenancyConfigCreate] = None,
        generative_config: Optional[_GenerativeProvider] = None,
        headers: Optional[Dict[str, str]] = None,
        ports: Tuple[int, int] = (8080, 50051),
        data_model_properties: Optional[Type[Properties]] = None,
        data_model_refs: Optional[Type[Properties]] = None,
        replication_config: Optional[_ReplicationConfigCreate] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        description: Optional[str] = None,
        reranker_config: Optional[_RerankerProvider] = None,
    ) -> Collection[Any, Any]:
        try:
            nonlocal client_fixture, name_fixtures, call_counter
            call_counter += 1
            name_fixture = (
                _sanitize_collection_name(request.node.fspath.basename + "_" + request.node.name)
                + name
                + "_"
                + str(call_counter)
            )
            name_fixtures.append(name_fixture)
            client_fixture = client_factory(
                headers=headers,
                ports=ports,
            )
            client_fixture.collections.delete(name_fixture)
            collection: Collection[Any, Any] = client_fixture.collections.create(
                name=name_fixture,
                description=description,
                vectorizer_config=vectorizer_config or Configure.Vectorizer.none(),
                properties=properties,
                references=references,
                inverted_index_config=inverted_index_config,
                multi_tenancy_config=multi_tenancy_config,
                generative_config=generative_config,
                data_model_properties=data_model_properties,
                data_model_references=data_model_refs,
                replication_config=replication_config,
                vector_index_config=vector_index_config,
                reranker_config=reranker_config,
            )
            return collection
        except Exception as e:
            print("Got exception in _factory", e)
            raise e

    try:
        yield _factory
    except Exception as e:
        print("Got exception in collection_factory", e)
        raise e
    finally:
        if client_fixture is not None and name_fixtures is not None:
            for name_fixture in name_fixtures:
                client_fixture.collections.delete(name_fixture)


class AsyncCollectionFactory(Protocol):
    """Typing for fixture."""

    async def __call__(
        self,
        name: str = "",
        properties: Optional[List[Property]] = None,
        references: Optional[List[_ReferencePropertyBase]] = None,
        vectorizer_config: Optional[
            Union[_VectorizerConfigCreate, List[_NamedVectorConfigCreate]]
        ] = None,
        inverted_index_config: Optional[_InvertedIndexConfigCreate] = None,
        multi_tenancy_config: Optional[_MultiTenancyConfigCreate] = None,
        generative_config: Optional[_GenerativeProvider] = None,
        headers: Optional[Dict[str, str]] = None,
        ports: Tuple[int, int] = (8080, 50051),
        data_model_properties: Optional[Type[Properties]] = None,
        data_model_refs: Optional[Type[Properties]] = None,
        replication_config: Optional[_ReplicationConfigCreate] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        description: Optional[str] = None,
        reranker_config: Optional[_RerankerProvider] = None,
    ) -> CollectionAsync[Any, Any]:
        """Typing for fixture."""
        ...


class AsyncClientFactory(Protocol):
    """Typing for fixture."""

    async def __call__(
        self,
        headers: Optional[Dict[str, str]] = None,
        ports: Tuple[int, int] = (8080, 50051),
    ) -> weaviate.WeaviateAsyncClient:
        """Typing for fixture."""
        ...


@pytest_asyncio.fixture
async def async_client_factory() -> AsyncGenerator[AsyncClientFactory, None]:
    client_fixture: Optional[weaviate.WeaviateAsyncClient] = None

    async def _factory(
        headers: Optional[Dict[str, str]] = None,
        ports: Tuple[int, int] = (8080, 50051),
    ) -> weaviate.WeaviateAsyncClient:
        nonlocal client_fixture
        if client_fixture is None:
            client_fixture = weaviate.use_async_with_local(
                headers=headers,
                grpc_port=ports[1],
                port=ports[0],
                additional_config=AdditionalConfig(timeout=(60, 120)),  # for image tests
            )
            await client_fixture.connect()
        return client_fixture

    try:
        yield _factory
    finally:
        if client_fixture is not None:
            await client_fixture.close()


@pytest_asyncio.fixture
async def async_collection_factory(
    request: SubRequest, async_client_factory: AsyncClientFactory
) -> AsyncGenerator[AsyncCollectionFactory, None]:
    name_fixtures: List[str] = []
    client_fixture: Optional[weaviate.WeaviateAsyncClient] = None

    async def _factory(
        name: str = "",
        properties: Optional[List[Property]] = None,
        references: Optional[List[_ReferencePropertyBase]] = None,
        vectorizer_config: Optional[
            Union[_VectorizerConfigCreate, List[_NamedVectorConfigCreate]]
        ] = None,
        inverted_index_config: Optional[_InvertedIndexConfigCreate] = None,
        multi_tenancy_config: Optional[_MultiTenancyConfigCreate] = None,
        generative_config: Optional[_GenerativeProvider] = None,
        headers: Optional[Dict[str, str]] = None,
        ports: Tuple[int, int] = (8080, 50051),
        data_model_properties: Optional[Type[Properties]] = None,
        data_model_refs: Optional[Type[Properties]] = None,
        replication_config: Optional[_ReplicationConfigCreate] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        description: Optional[str] = None,
        reranker_config: Optional[_RerankerProvider] = None,
    ) -> CollectionAsync[Any, Any]:
        try:
            nonlocal client_fixture, name_fixtures
            name_fixture = _sanitize_collection_name(request.node.name) + name
            name_fixtures.append(name_fixture)
            client_fixture = await async_client_factory(
                headers=headers,
                ports=ports,
            )
            collection: CollectionAsync[Any, Any] = await client_fixture.collections.create(
                name=name_fixture,
                description=description,
                vectorizer_config=vectorizer_config or Configure.Vectorizer.none(),
                properties=properties,
                references=references,
                inverted_index_config=inverted_index_config,
                multi_tenancy_config=multi_tenancy_config,
                generative_config=generative_config,
                data_model_properties=data_model_properties,
                data_model_references=data_model_refs,
                replication_config=replication_config,
                vector_index_config=vector_index_config,
                reranker_config=reranker_config,
            )
            return collection
        except Exception as e:
            print("Got exception in _factory", e)
            raise e

    try:
        yield _factory
    except Exception as e:
        print("Got exception in collection_factory", e)
        raise e
    finally:
        if client_fixture is not None and name_fixtures is not None:
            for name_fixture in name_fixtures:
                await client_fixture.collections.delete(name_fixture)


class OpenAICollection(Protocol):
    """Typing for fixture."""

    def __call__(
        self,
        name: str = "",
        vectorizer_config: Optional[
            Union[_VectorizerConfigCreate, List[_NamedVectorConfigCreate]]
        ] = None,
    ) -> Collection[Any, Any]:
        """Typing for fixture."""
        ...


@pytest.fixture
def openai_collection(
    collection_factory: CollectionFactory,
) -> Generator[OpenAICollection, None, None]:
    def _factory(
        name: str = "",
        vectorizer_config: Optional[
            Union[_VectorizerConfigCreate, List[_NamedVectorConfigCreate]]
        ] = None,
    ) -> Collection[Any, Any]:
        api_key = os.environ.get("OPENAI_APIKEY")
        if api_key is None:
            pytest.skip("No OpenAI API key found.")

        if vectorizer_config is None:
            vectorizer_config = Configure.Vectorizer.none()

        collection = collection_factory(
            name=name,
            vectorizer_config=vectorizer_config or Configure.Vectorizer.none(),
            properties=[
                Property(name="text", data_type=DataType.TEXT),
                Property(name="content", data_type=DataType.TEXT),
                Property(name="extra", data_type=DataType.TEXT),
            ],
            generative_config=Configure.Generative.openai(),
            ports=(8086, 50057),
            headers={"X-OpenAI-Api-Key": api_key},
        )

        return collection

    yield _factory


class AsyncOpenAICollectionFactory(Protocol):
    """Typing for fixture."""

    async def __call__(
        self,
        name: str = "",
        vectorizer_config: Optional[
            Union[_VectorizerConfigCreate, List[_NamedVectorConfigCreate]]
        ] = None,
    ) -> CollectionAsync[Any, Any]:
        """Typing for fixture."""
        ...


@pytest_asyncio.fixture
async def async_openai_collection(
    async_collection_factory: AsyncCollectionFactory,
) -> AsyncGenerator[AsyncOpenAICollectionFactory, None]:
    async def _factory(
        name: str = "",
        vectorizer_config: Optional[
            Union[_VectorizerConfigCreate, List[_NamedVectorConfigCreate]]
        ] = None,
    ) -> CollectionAsync[Any, Any]:
        api_key = os.environ.get("OPENAI_APIKEY")
        if api_key is None:
            pytest.skip("No OpenAI API key found.")

        if vectorizer_config is None:
            vectorizer_config = Configure.Vectorizer.none()

        collection = await async_collection_factory(
            name=name,
            vectorizer_config=vectorizer_config or Configure.Vectorizer.none(),
            properties=[
                Property(name="text", data_type=DataType.TEXT),
                Property(name="content", data_type=DataType.TEXT),
                Property(name="extra", data_type=DataType.TEXT),
            ],
            generative_config=Configure.Generative.openai(),
            ports=(8086, 50057),
            headers={"X-OpenAI-Api-Key": api_key},
        )

        return collection

    yield _factory


class CollectionFactoryGet(Protocol):
    """Typing for fixture."""

    def __call__(
        self,
        name: str,
        data_model_props: Optional[Type[Properties]] = None,
        data_model_refs: Optional[Type[Properties]] = None,
        skip_argument_validation: bool = False,
    ) -> Collection[Any, Any]:
        """Typing for fixture."""
        ...


@pytest.fixture
def collection_factory_get(
    client_factory: ClientFactory,
) -> Generator[CollectionFactoryGet, None, None]:
    name_fixture: Optional[str] = None

    def _factory(
        name: str,
        data_model_props: Optional[Type[Properties]] = None,
        data_model_refs: Optional[Type[Properties]] = None,
        skip_argument_validation: bool = False,
    ) -> Collection[Any, Any]:
        nonlocal name_fixture
        name_fixture = _sanitize_collection_name(name)
        collection: Collection[Any, Any] = client_factory().collections.get(
            name=name_fixture,
            data_model_properties=data_model_props,
            data_model_references=data_model_refs,
            skip_argument_validation=skip_argument_validation,
        )
        return collection

    yield _factory


def _sanitize_collection_name(name: str) -> str:
    name = name.replace("[", "").replace("]", "").replace("-", "").replace(" ", "").replace(".", "")
    return name[0].upper() + name[1:]
