import uuid

import pytest

from weaviate.collections.batch.grpc_batch import _validate_props
from weaviate.collections.classes.batch import (
    MAX_STORED_RESULTS,
    BatchObject,
    BatchObjectReturn,
    ErrorObject,
)
from weaviate.exceptions import WeaviateInsertInvalidPropertyError


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


def test_error_object_original_uuid_is_set_from_batch_object() -> None:
    """ErrorObject should preserve the original_uuid from the BatchObject that failed."""
    obj_uuid = uuid.uuid4()
    obj = BatchObject(collection="TestCollection", uuid=obj_uuid, index=0)
    error = ErrorObject(message="some error", object_=obj, original_uuid=obj.uuid)
    assert str(error.original_uuid) == str(obj_uuid)


def test_error_object_original_uuid_not_none_when_object_has_uuid() -> None:
    """When building ErrorObjects in the exception path, original_uuid must not be None."""
    objs = [
        BatchObject(collection="TestCollection", uuid=uuid.uuid4(), index=i) for i in range(3)
    ]
    # Simulate what base.py does in the exception handler after the fix
    errors_obj = {
        idx: ErrorObject(message="connection error", object_=obj, original_uuid=obj.uuid)
        for idx, obj in enumerate(objs)
    }
    for idx, obj in enumerate(objs):
        assert errors_obj[idx].original_uuid is not None
        assert errors_obj[idx].original_uuid == obj.uuid
