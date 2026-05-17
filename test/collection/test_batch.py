import uuid

import pytest

from weaviate.collections.batch.grpc_batch import _validate_props
from weaviate.collections.classes.batch import MAX_STORED_RESULTS, BatchObjectReturn, BatchReference
from weaviate.exceptions import WeaviateInsertInvalidPropertyError
from weaviate.types import BEACON


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


@pytest.mark.parametrize(
    ("to_object_collection", "expected_to"),
    [
        (None, f"{BEACON}28f3f61b-b524-45e0-9bbe-2c1550bf73d2"),
        ("Target", f"{BEACON}Target/28f3f61b-b524-45e0-9bbe-2c1550bf73d2"),
    ],
)
def test_batch_reference_to_internal_is_idempotent(
    to_object_collection: str | None, expected_to: str
) -> None:
    ref = BatchReference(
        from_object_collection="Source",
        from_object_uuid="1c9cd584-88fe-5010-83d0-017cb3fcb446",
        from_property_name="link",
        to_object_collection=to_object_collection,
        to_object_uuid="28f3f61b-b524-45e0-9bbe-2c1550bf73d2",
        index=0,
    )

    first = ref._to_internal()
    second = ref._to_internal()

    assert ref.to_object_collection == to_object_collection
    assert first.to == expected_to
    assert second.to == expected_to
