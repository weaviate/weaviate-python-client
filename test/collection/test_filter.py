import pytest
import weaviate.classes as wvc

import weaviate


def test_empty_input_contains_any() -> None:
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError):
        wvc.query.Filter.by_id().contains_any([])
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError):
        wvc.query.Filter.by_property("test").contains_any([])


def test_empty_input_contains_all() -> None:
    with pytest.raises(weaviate.exceptions.WeaviateInvalidInputError):
        wvc.query.Filter.by_property("test").contains_all([])
