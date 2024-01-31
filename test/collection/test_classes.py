import pytest
from pydantic import ValidationError

from weaviate.collections.classes.grpc import (
    QueryReference,
    _QueryReferenceMultiTarget,
    _QueryReference,
    Sort,
)

from weaviate.collections.classes.filters import Filter


def test_link_to_errors_on_extra_variable() -> None:
    with pytest.raises(ValidationError):
        QueryReference(link_on="ref", return_property="name")


def test_link_to_multi_target_errors_on_extra_variable() -> None:
    with pytest.raises(ValidationError):
        _QueryReferenceMultiTarget(link_on="ref", target_colection="Test")


def test_link_to_multi_target_is_link_to() -> None:
    link_to = _QueryReferenceMultiTarget(link_on="ref", target_collection="Test")
    assert isinstance(link_to, _QueryReference)


def test_direct_init_filter() -> None:
    with pytest.raises(TypeError):
        Filter()


def test_direct_init_sort() -> None:
    with pytest.raises(TypeError):
        Sort()
