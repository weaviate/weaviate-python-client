import pytest
from pydantic import ValidationError

from weaviate.collections.classes.grpc import FromReference, FromReferenceMultiTarget


def test_link_to_errors_on_extra_variable():
    with pytest.raises(ValidationError):
        FromReference(link_on="ref", return_property="name")


def test_link_to_multi_target_errors_on_extra_variable():
    with pytest.raises(ValidationError):
        FromReferenceMultiTarget(link_on="ref", target_colection="Test")


def test_link_to_multi_target_is_link_to():
    link_to = FromReferenceMultiTarget(link_on="ref", target_collection="Test")
    assert isinstance(link_to, FromReference)
