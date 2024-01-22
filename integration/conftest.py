import os
import weakref
from typing import Any, Optional, List, Generator, Protocol, Type, Dict, Tuple

import pytest
from _pytest.fixtures import SubRequest

import weaviate
from weaviate.collections import Collection
from weaviate.collections.classes.config import (
    Property,
    _VectorizerConfigCreate,
    _InvertedIndexConfigCreate,
    _ReferencePropertyBase,
    Configure,
    _GenerativeConfigCreate,
    _ReplicationConfigCreate,
    DataType,
    _MultiTenancyConfigCreate,
    _VectorIndexConfigCreate,
    _RerankerConfigCreate,
    ConsistencyLevel,
)
from weaviate.collections.classes.types import Properties


class CollectionFactory(Protocol):
    """Typing for fixture."""

    def __call__(
        self,
        name: str = "",
        properties: Optional[List[Property]] = None,
        references: Optional[List[_ReferencePropertyBase]] = None,
        vectorizer_config: Optional[_VectorizerConfigCreate] = None,
        inverted_index_config: Optional[_InvertedIndexConfigCreate] = None,
        multi_tenancy_config: Optional[_MultiTenancyConfigCreate] = None,
        generative_config: Optional[_GenerativeConfigCreate] = None,
        headers: Optional[Dict[str, str]] = None,
        ports: Tuple[int, int] = (8080, 50051),
        data_model_properties: Optional[Type[Properties]] = None,
        data_model_refs: Optional[Type[Properties]] = None,
        replication_config: Optional[_ReplicationConfigCreate] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        description: Optional[str] = None,
        reranker_config: Optional[_RerankerConfigCreate] = None,
        consistency_level: Optional[ConsistencyLevel] = None,
    ) -> Collection[Any, Any]:
        """Typing for fixture."""
        ...


@pytest.fixture
def collection_factory(request: SubRequest) -> Generator[CollectionFactory, None, None]:
    client_fixture: Optional[weaviate.WeaviateClient] = None
    collections: List[weakref.finalize] = []

    def cleanup_collection(client: Optional[weaviate.WeaviateClient], name: str) -> None:
        if client is not None:
            client.collections.delete(name)

    def cleanup_client(client: Optional[weaviate.WeaviateClient]) -> None:
        if client is not None:
            client.close()

    def _factory(
        name: str = "",
        properties: Optional[List[Property]] = None,
        references: Optional[List[_ReferencePropertyBase]] = None,
        vectorizer_config: Optional[_VectorizerConfigCreate] = None,
        inverted_index_config: Optional[_InvertedIndexConfigCreate] = None,
        multi_tenancy_config: Optional[_MultiTenancyConfigCreate] = None,
        generative_config: Optional[_GenerativeConfigCreate] = None,
        headers: Optional[Dict[str, str]] = None,
        ports: Tuple[int, int] = (8080, 50051),
        data_model_properties: Optional[Type[Properties]] = None,
        data_model_refs: Optional[Type[Properties]] = None,
        replication_config: Optional[_ReplicationConfigCreate] = None,
        vector_index_config: Optional[_VectorIndexConfigCreate] = None,
        description: Optional[str] = None,
        reranker_config: Optional[_RerankerConfigCreate] = None,
        consistency_level: Optional[ConsistencyLevel] = None,
    ) -> Collection[Any, Any]:
        nonlocal client_fixture, collections

        name_fixture = _sanitize_collection_name(request.node.name) + name
        client_fixture = weaviate.connect_to_local(
            headers=headers, grpc_port=ports[1], port=ports[0]
        )
        client_fixture.collections.delete(name_fixture)

        collection: Collection[Any, Any] = client_fixture.collections.create(
            name=name_fixture,
            description=description,
            vectorizer_config=vectorizer_config,
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
        if consistency_level is not None:
            collection = collection.with_consistency_level(consistency_level)

        # Create a weak reference to the collection with a cleanup callback
        finalizer = weakref.finalize(collection, cleanup_collection, client_fixture, name_fixture)
        collections.append(finalizer)

        return collection

    try:
        yield _factory
    except Exception as e:
        raise e
    finally:
        # Check if all collections have been cleared
        if all(f() is None for f in collections):
            cleanup_client(client_fixture)


class OpenAICollection(Protocol):
    """Typing for fixture."""

    def __call__(
        self, name: str = "", vectorizer_config: Optional[_VectorizerConfigCreate] = None
    ) -> Collection[Any, Any]:
        """Typing for fixture."""
        ...


@pytest.fixture
def openai_collection(
    collection_factory: CollectionFactory,
) -> Generator[OpenAICollection, None, None]:
    def _factory(
        name: str = "", vectorizer_config: Optional[_VectorizerConfigCreate] = None
    ) -> Collection[Any, Any]:
        api_key = os.environ.get("OPENAI_APIKEY")
        if api_key is None:
            pytest.skip("No OpenAI API key found.")

        if vectorizer_config is None:
            vectorizer_config = Configure.Vectorizer.none()

        collection = collection_factory(
            name=name,
            vectorizer_config=vectorizer_config,
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
    ) -> Collection[Any, Any]:
        """Typing for fixture."""
        ...


@pytest.fixture
def collection_factory_get() -> Generator[CollectionFactoryGet, None, None]:
    client_fixture: Optional[weaviate.WeaviateClient] = None
    collections: List[weakref.finalize] = []
    names_fixture: List[str] = []

    def cleanup_collection() -> None:
        pass

    def cleanup_client(client: Optional[weaviate.WeaviateClient], names_fixture: List[str]) -> None:
        if client is not None:
            client.collections.delete(names_fixture)
            client.close()

    def _factory(
        name: str,
        data_model_props: Optional[Type[Properties]] = None,
        data_model_refs: Optional[Type[Properties]] = None,
    ) -> Collection[Any, Any]:
        nonlocal client_fixture
        name_fixture = _sanitize_collection_name(name)
        client_fixture = weaviate.connect_to_local()

        collection: Collection[Any, Any] = client_fixture.collections.get(
            name=name_fixture,
            data_model_properties=data_model_props,
            data_model_references=data_model_refs,
        )

        names_fixture.append(name_fixture)
        # Create a weak reference to the collection with a cleanup callback
        finalizer = weakref.finalize(collection, cleanup_collection)
        collections.append(finalizer)

        return collection

    try:
        yield _factory
    except Exception as e:
        raise e
    finally:
        if all(f() is None for f in collections):
            cleanup_client(client_fixture, names_fixture)


def _sanitize_collection_name(name: str) -> str:
    name = name.replace("[", "").replace("]", "").replace("-", "").replace(" ", "").replace(".", "")
    return name[0].upper() + name[1:]
