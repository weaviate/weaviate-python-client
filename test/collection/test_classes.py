import pytest
import uuid
from weaviate.collection.classes import ReferenceTo, ReferenceToMultiTarget, _ReferenceDataType


def test_raises_error_when_reference_to_used_incorrectly():
    ref_dtype = _ReferenceDataType(
        collections=["Foo", "Bar"],
    )
    ref_to = ReferenceTo(
        uuids=uuid.uuid4(),
    )
    with pytest.raises(ValueError) as error:
        ref_to.to_beacons_strict(ref_dtype)
        assert (
            error
            == "Can only use ReferenceTo on a reference property with a single target collection, use ReferenceToMultiTarget instead"
        )


def test_raises_error_when_target_collection_required_and_wrong():
    ref_dtype = _ReferenceDataType(
        collections=["Foo", "Bar"],
    )
    ref_to = ReferenceToMultiTarget(
        uuids=uuid.uuid4(),
        target_collection="Baz",
    )
    with pytest.raises(ValueError) as error:
        ref_to.to_beacons_strict(ref_dtype)
        assert (
            error
            == 'target_collection must be one of ["Foo", "Bar"] since these are the collections specified in the reference property of this collection but got "Baz" instead'
        )
