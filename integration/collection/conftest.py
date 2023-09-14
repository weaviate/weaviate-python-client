from typing import Dict, List, Optional, Protocol, Type, Union

import pytest
import requests

from weaviate.collection import Collection, CollectionObject
from weaviate.collection.classes.config import (
    _GenerativeConfig,
    _InvertedIndexConfigCreate,
    _MultiTenancyConfigCreate,
    Property,
    _ShardingConfigCreate,
    ReferencePropertyBase,
    _ReplicationConfigCreate,
    _VectorizerConfig,
    _VectorIndexConfigCreate,
    VectorIndexType,
)
from weaviate.collection.classes.types import Properties
from weaviate.config import Config
from weaviate.connect import Connection


class CollectionObjectFactory(Protocol):
    """Typing for fixture."""

    def __call__(
        self,
        rest_port: int,
        grpc_port: int,
        name: str,
        description: Optional[str] = None,
        data_model: Optional[Type[Properties]] = None,
        generative_search: Optional[_GenerativeConfig] = None,
        inverted_index_config: Optional[_InvertedIndexConfigCreate] = None,
        multi_tenancy_config: Optional[_MultiTenancyConfigCreate] = None,
        properties: Optional[List[Union[Property, ReferencePropertyBase]]] = None,
        replication_config: Optional[_ReplicationConfigCreate] = None,
        sharding_config: Optional[_ShardingConfigCreate] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vector_index_type: VectorIndexType = VectorIndexType.HNSW,
        vectorizer_config: Optional[_VectorizerConfig] = None,
        additional_headers: Dict[str, str] = None,
    ) -> CollectionObject[Properties]:
        """Typing for fixture."""
        ...


@pytest.fixture
def collection_object_factory() -> CollectionObjectFactory:
    name_fixture: str
    collection_fixture: Optional[Collection] = None

    def _factory(
        rest_port: int,
        grpc_port: int,
        name: str,
        description: Optional[str] = None,
        data_model: Optional[Type[Properties]] = None,
        generative_search: Optional[_GenerativeConfig] = None,
        inverted_index_config: Optional[_InvertedIndexConfigCreate] = None,
        multi_tenancy_config: Optional[_MultiTenancyConfigCreate] = None,
        properties: Optional[List[Union[Property, ReferencePropertyBase]]] = None,
        replication_config: Optional[_ReplicationConfigCreate] = None,
        sharding_config: Optional[_ShardingConfigCreate] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        vector_index_type: VectorIndexType = VectorIndexType.HNSW,
        vectorizer_config: Optional[_VectorizerConfig] = None,
        additional_headers: Dict[str, str] = None,
    ) -> CollectionObject[Properties]:
        nonlocal collection_fixture, name_fixture
        name_fixture = name
        config = Config(grpc_port_experimental=grpc_port)
        connection = Connection(
            url=f"http://localhost:{rest_port}",
            auth_client_secret=None,
            timeout_config=(10, 60),
            proxies=None,
            trust_env=False,
            additional_headers=additional_headers,
            startup_period=5,
            connection_config=config.connection_config,
            embedded_db=None,
            grcp_port=config.grpc_port_experimental,
        )
        collection_fixture = Collection(connection)
        collection_fixture.delete(name)

        collection_object = collection_fixture.create(
            name=name,
            data_model=data_model,
            description=description,
            generative_search=generative_search,
            inverted_index_config=inverted_index_config,
            multi_tenancy_config=multi_tenancy_config,
            properties=properties,
            replication_config=replication_config,
            sharding_config=sharding_config,
            vector_index_config=vector_index_config,
            vector_index_type=vector_index_type,
            vectorizer_config=vectorizer_config,
        )
        return collection_object

    yield _factory
    if collection_fixture is not None:
        collection_fixture.delete(name_fixture)  # type: ignore


def _collection(rest: int, grpc: int, headers: Dict[str, str]):
    config = Config(grpc_port_experimental=grpc)
    connection = Connection(
        url=f"http://localhost:{rest}",
        auth_client_secret=None,
        timeout_config=(10, 60),
        proxies=None,
        trust_env=False,
        additional_headers=headers,
        startup_period=5,
        connection_config=config.connection_config,
        embedded_db=None,
        grcp_port=config.grpc_port_experimental,
    )
    return Collection(connection)


def _clear(rest: int) -> None:
    res = requests.get(f"http://localhost:{rest}/v1/schema")
    if res.status_code == 200:
        schema = res.json()
        for class_ in schema["classes"]:
            res = requests.delete(f"http://localhost:{rest}/v1/schema/{class_['class']}")
            if res.status_code < 200 or res.status_code >= 300:
                raise Exception(f"Failed to delete the test data of {class_}: {res.text}")
    else:
        raise Exception(f"Failed retrieve the full schema: {res.text}")


@pytest.fixture(scope="module")
def collection_basic():
    try:
        yield _collection(8080, 50051, {})
    finally:
        _clear(8080)


@pytest.fixture(scope="function")
def request_id(request: pytest.FixtureRequest) -> str:
    return request.node.callspec.id.replace("-", "")  # type: ignore
