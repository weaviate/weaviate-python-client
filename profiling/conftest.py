import os

import pytest
from typing import Any, Optional, List, Generator, Protocol, Dict, Union

from _pytest.fixtures import SubRequest

import weaviate
from weaviate.collections import Collection
from weaviate.collections.classes.config import (
    _InvertedIndexConfigCreate,
    Property,
    _VectorizerConfigCreate,
)
from weaviate.config import AdditionalConfig

from weaviate.collections.classes.config_named_vectors import _NamedVectorConfigCreate

from weaviate.connect.integrations import _IntegrationConfig


def get_file_path(file_name: str) -> str:
    if not os.path.exists(file_name) and not os.path.exists("profiling/" + file_name):
        pytest.skip("data does not exist")
    if os.path.exists("profiling/" + file_name):
        file_name = "profiling/" + file_name
    return file_name


class CollectionFactory(Protocol):
    """Typing for fixture."""

    def __call__(
        self,
        properties: Optional[List[Property]] = None,
        vectorizer_config: Optional[
            Union[_VectorizerConfigCreate, List[_NamedVectorConfigCreate]]
        ] = None,
        headers: Optional[Dict[str, str]] = None,
        inverted_index_config: Optional[_InvertedIndexConfigCreate] = None,
        integration_config: Optional[Union[_IntegrationConfig, List[_IntegrationConfig]]] = None,
    ) -> Collection[Any, Any]:
        """Typing for fixture."""
        ...


@pytest.fixture
def collection_factory(request: SubRequest) -> Generator[CollectionFactory, None, None]:
    name_fixture: Optional[str] = None
    client_fixture: Optional[weaviate.WeaviateClient] = None

    def _factory(
        properties: Optional[List[Property]] = None,
        vectorizer_config: Optional[
            Union[_VectorizerConfigCreate, List[_NamedVectorConfigCreate]]
        ] = None,
        headers: Optional[Dict[str, str]] = None,
        inverted_index_config: Optional[_InvertedIndexConfigCreate] = None,
        integration_config: Optional[Union[_IntegrationConfig, List[_IntegrationConfig]]] = None,
    ) -> Collection[Any, Any]:
        nonlocal client_fixture, name_fixture
        name_fixture = _sanitize_collection_name(request.node.name)
        client_fixture = weaviate.connect_to_local(
            headers=headers,
            additional_config=AdditionalConfig(timeout=(60, 120)),  # for image tests
        )
        client_fixture.collections.delete(name_fixture)
        if integration_config is not None:
            client_fixture.integrations.configure(integration_config)

        collection: Collection[Any, Any] = client_fixture.collections.create(
            name=name_fixture,
            vectorizer_config=vectorizer_config,
            properties=properties,
            inverted_index_config=inverted_index_config,
        )
        return collection

    try:
        yield _factory
    finally:
        if client_fixture is not None and name_fixture is not None:
            client_fixture.collections.delete(name_fixture)
            client_fixture.close()


def _sanitize_collection_name(name: str) -> str:
    name = name.replace("[", "").replace("]", "").replace("-", "").replace(" ", "").replace(".", "")
    return name[0].upper() + name[1:]
