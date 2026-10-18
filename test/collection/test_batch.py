import uuid

import pytest

from weaviate.collections.batch.base import _RateLimitedBatching
from weaviate.collections.batch.grpc_batch import _BatchGRPC, _validate_props
from weaviate.collections.classes.batch import (
    MAX_STORED_RESULTS,
    BatchObject,
    BatchObjectReturn,
    BatchReference,
    BatchReferenceReturn,
    ErrorObject,
    ErrorReference,
)
from weaviate.collections.classes.internal import ReferenceToMulti
from weaviate.exceptions import WeaviateInsertInvalidPropertyError
from weaviate.proto.v1 import batch_pb2
from weaviate.util import _ServerVersion


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


@pytest.mark.parametrize(
    ("number_objects", "elapsed_time", "expected_sleep_time"),
    [
        (500, 0, 31),
        (100, 0, 6.2),
        (100, 2, 4.2),
        (100, -62, 68.2),
        (100, 7, 0),
        (0, 0, 0),
    ],
)
def test_rate_limited_batching_sleep_time_uses_previous_batch_size(
    number_objects: int, elapsed_time: float, expected_sleep_time: float
) -> None:
    batching = _RateLimitedBatching(requests_per_minute=1000)

    assert batching.get_sleep_time(
        number_objects=number_objects,
        elapsed_time=elapsed_time,
        base_time=62,
    ) == pytest.approx(expected_sleep_time)


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


@pytest.mark.parametrize("properties", [None, {}, {"name": "source"}])
@pytest.mark.parametrize("reference_kind", ["single", "list", "multi"])
def test_grpc_batch_preserves_references(
    properties: dict[str, str] | None, reference_kind: str
) -> None:
    target = uuid.UUID("00000000-0000-0000-0000-000000000001")
    reference: uuid.UUID | list[uuid.UUID] | ReferenceToMulti
    if reference_kind == "multi":
        reference = ReferenceToMulti(target_collection="Target", uuids=[target])
    elif reference_kind == "list":
        reference = [target]
    else:
        reference = target
    obj = BatchObject(
        collection="Source", properties=properties, references={"related": reference}, index=0
    )
    encoded = _BatchGRPC(_ServerVersion(1, 36, 0), None, None).grpc_object(obj._to_internal())
    wire_object = batch_pb2.BatchObject.FromString(encoded.SerializeToString())

    if reference_kind == "multi":
        (ref,) = wire_object.properties.multi_target_ref_props
        assert ref.target_collection == "Target"
        assert not wire_object.properties.single_target_ref_props
    else:
        (ref,) = wire_object.properties.single_target_ref_props
        assert not wire_object.properties.multi_target_ref_props
    assert ref.prop_name == "related"
    assert list(ref.uuids) == [str(target)]
    assert dict(wire_object.properties.non_ref_properties) == (properties or {})


def test_grpc_batch_omits_properties_when_no_properties_or_references() -> None:
    obj = BatchObject(collection="Source", index=0)
    encoded = _BatchGRPC(_ServerVersion(1, 36, 0), None, None).grpc_object(obj._to_internal())
    assert not encoded.HasField("properties")
