import pytest
import uuid
from weaviate.collection.classes import ReferenceTo, _ReferenceDataType


def test_raises_error_when_which_collection_required_and_absent():
    ref_dtype = _ReferenceDataType(
        reference_collections=["Foo", "Bar"],
    )
    ref_to = ReferenceTo(
        reference_uuids=uuid.uuid4(),
    )
    with pytest.raises(ValueError) as error:
        ref_to.to_beacons(ref_dtype)
        assert (
            error
            == "which_collection must be specified when using a reference property with multiple target collections"
        )


def test_raises_error_when_which_collection_required_and_wrong():
    ref_dtype = _ReferenceDataType(
        reference_collections=["Foo", "Bar"],
    )
    ref_to = ReferenceTo(
        reference_uuids=uuid.uuid4(),
        which_collection="Baz",
    )
    with pytest.raises(ValueError) as error:
        ref_to.to_beacons(ref_dtype)
        assert (
            error
            == 'which_collection must be one of ["Foo", "Bar"] since these are the target collections specified in the reference property of this collection but got "Baz" instead'
        )
