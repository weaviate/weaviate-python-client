from typing import Any, Optional, List, Generator, Protocol

import pytest

import weaviate
from weaviate import Collection
from weaviate.collections.classes.config import (
    Property,
    _VectorizerConfigCreate,
    _InvertedIndexConfigCreate,
    _ReferencePropertyBase,
)


class CollectionFactory(Protocol):
    """Typing for fixture."""

    def __call__(
        self,
        name: str,
        properties: Optional[List[Property]] = None,
        references: Optional[List[_ReferencePropertyBase]] = None,
        vectorizer_config: Optional[_VectorizerConfigCreate] = None,
        inverted_index_config: Optional[_InvertedIndexConfigCreate] = None,
    ) -> Collection[Any, Any]:
        """Typing for fixture."""
        ...


@pytest.fixture
def collection_factory() -> (
    Generator[
        CollectionFactory,
        None,
        None,
    ]
):
    name_fixture: Optional[str] = None
    client_fixture: Optional[weaviate.WeaviateClient] = None

    def _factory(
        name: str,
        properties: Optional[List[Property]] = None,
        references: Optional[List[_ReferencePropertyBase]] = None,
        vectorizer_config: Optional[_VectorizerConfigCreate] = None,
        inverted_index_config: Optional[_InvertedIndexConfigCreate] = None,
    ) -> Collection[Any, Any]:
        nonlocal client_fixture, name_fixture
        name_fixture = _sanitize_collection_name(name)
        client_fixture = weaviate.connect_to_local()
        client_fixture.collections.delete(name_fixture)

        collection: Collection[Any, Any] = client_fixture.collections.create(
            name=name_fixture,
            vectorizer_config=vectorizer_config,
            properties=properties,
            references=references,
            inverted_index_config=inverted_index_config,
        )
        return collection

    yield _factory
    if client_fixture is not None and name_fixture is not None:
        client_fixture.collections.delete(name_fixture)


def _sanitize_collection_name(name: str) -> str:
    name = name.replace("[", "").replace("]", "").replace("-", "")
    return name[0].upper() + name[1:]
