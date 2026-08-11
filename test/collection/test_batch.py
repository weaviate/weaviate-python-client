import uuid

import pytest

from weaviate.collections.batch.grpc_batch import _validate_props
from weaviate.collections.classes.batch import (
    MAX_STORED_RESULTS,
    BatchObject,
    BatchObjectReturn,
    BatchReference,
    BatchReferenceReturn,
    ErrorObject,
    ErrorReference,
)
from weaviate.exceptions import WeaviateInsertInvalidPropertyError


def _error_object(index: int) -> ErrorObject:
    return ErrorObject(
        message="something went wrong",
        object_=BatchObject(collection="Test", properties={"name": "test"}, index=index),
    )


def _error_reference(index: int) -> ErrorReference:
    return ErrorReference(
        message="something went wrong",
        reference=BatchReference(
            from_object_collection="Test",
            from_object_uuid=uuid.uuid4(),
            from_property_name="other",
            to_object_uuid=uuid.uuid4(),
            index=index,
        ),
    )


def test_batch_object_return_add() -> None:
    lhs_uuids = [uuid.uuid4() for _ in range(MAX_STORED_RESULTS)]
    lhs = BatchObjectReturn(
        _all_responses=lhs_uuids,
        elapsed_seconds=0.1,
        errors={},
        has_errors=False,
        uuids=dict(e for e in enumerate(lhs_uuids)),
    )
    rhs_uuids = [uuid.uuid4() for _ in range(2)]
    rhs = BatchObjectReturn(
        _all_responses=rhs_uuids,
        elapsed_seconds=0.1,
        errors={},
        has_errors=False,
        uuids={
            MAX_STORED_RESULTS: rhs_uuids[0],
            MAX_STORED_RESULTS + 1: rhs_uuids[1],
        },
    )
    result = lhs + rhs
    assert len(result.all_responses) == MAX_STORED_RESULTS
    assert len(result.uuids) == MAX_STORED_RESULTS
    assert result.uuids == {
        idx + len(rhs_uuids): v
        for idx, v in enumerate(lhs_uuids[len(rhs_uuids) : MAX_STORED_RESULTS] + rhs_uuids)
    }


def test_batch_object_return_has_errors_when_constructed_with_errors() -> None:
    err = _error_object(0)
    result = BatchObjectReturn(_all_responses=[err], errors={0: err})
    assert result.has_errors


def test_batch_object_return_add_sets_has_errors() -> None:
    err = _error_object(1)
    result = BatchObjectReturn()
    result += BatchObjectReturn(_all_responses=[uuid.uuid4()], uuids={0: uuid.uuid4()})
    result += BatchObjectReturn(_all_responses=[err], errors={1: err})
    assert result.has_errors
    assert len(result.errors) == 1


def test_batch_object_return_has_no_errors_when_all_succeed() -> None:
    uid = uuid.uuid4()
    result = BatchObjectReturn()
    result += BatchObjectReturn(_all_responses=[uid], uuids={0: uid})
    assert not result.has_errors


def test_batch_reference_return_has_errors_when_constructed_with_errors() -> None:
    err = _error_reference(0)
    result = BatchReferenceReturn(errors={0: err})
    assert result.has_errors


def test_batch_reference_return_add_sets_has_errors() -> None:
    err = _error_reference(0)
    result = BatchReferenceReturn()
    result += BatchReferenceReturn(errors={0: err})
    assert result.has_errors
    assert len(result.errors) == 1


def test_validate_props_raises_for_top_level_id() -> None:
    with pytest.raises(WeaviateInsertInvalidPropertyError):
        _validate_props({"id": "abc123"})


def test_validate_props_allows_nested_id() -> None:
    _validate_props({"id": "abc123"}, nested=True)


def test_validate_props_raises_for_top_level_vector() -> None:
    with pytest.raises(WeaviateInsertInvalidPropertyError):
        _validate_props({"vector": [0.1, 0.2]})


def test_validate_props_raises_for_nested_vector() -> None:
    with pytest.raises(WeaviateInsertInvalidPropertyError):
        _validate_props({"vector": [0.1, 0.2]}, nested=True)
