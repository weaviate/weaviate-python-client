import copy
import datetime
import uuid
from collections import UserList
from typing import Any

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
from weaviate.exceptions import WeaviateInsertInvalidPropertyError
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


@pytest.mark.parametrize("sequence", [list, tuple, UserList])
@pytest.mark.parametrize(
    ("values", "field"),
    [
        ([], "empty_list_props"),
        ([True, False], "boolean_array_properties"),
        (["", "text"], "text_array_properties"),
        ([2**53 + 1, -(2**53 + 1)], "int_array_properties"),
        ([0.1, -2.5], "number_array_properties"),
        ([datetime.datetime(2026, 1, 2, tzinfo=datetime.timezone.utc)], "text_array_properties"),
        ([uuid.UUID("12345678-1234-5678-1234-567812345678")], "text_array_properties"),
        ([{"id": "nested", "value": "text"}], "object_array_properties"),
    ],
)
def test_batch_property_sequences_match_lists(sequence: Any, values: Any, field: str) -> None:
    grpc = _BatchGRPC(_ServerVersion(1, 40, 0), None, None)
    properties = {"value": sequence(values)}
    original = copy.deepcopy(properties)

    def encode(props: Any) -> Any:
        return grpc.grpc_object(
            BatchObject(collection="Test", properties=props, index=0)._to_internal()
        )

    actual = encode(properties).properties
    expected = encode({"value": values}).properties
    assert actual == expected
    assert len(getattr(actual, field)) == 1
    if field == "int_array_properties":
        assert list(actual.int_array_properties[0].values) == values
    assert properties == original
    assert isinstance(properties["value"], sequence)


@pytest.mark.parametrize("sequence", [list, tuple, UserList])
def test_batch_nested_property_sequences_match_lists(sequence: Any) -> None:
    grpc = _BatchGRPC(_ServerVersion(1, 40, 0), None, None)
    child = {"integers": sequence([2**53 + 1]), "empty": sequence([])}
    properties = {"nested": {"objects": sequence([child])}}
    original = copy.deepcopy(properties)
    expected = {"nested": {"objects": [{"integers": [2**53 + 1], "empty": []}]}}
    actual = grpc.grpc_object(
        BatchObject(collection="Test", properties=properties, index=0)._to_internal()
    ).properties
    assert (
        actual
        == grpc.grpc_object(
            BatchObject(collection="Test", properties=expected, index=0)._to_internal()
        ).properties
    )
    assert properties == original


@pytest.mark.parametrize("value", ["", "text", True, 3, 1.5, None])
def test_batch_scalar_properties_remain_scalars(value: Any) -> None:
    grpc = _BatchGRPC(_ServerVersion(1, 40, 0), None, None)
    actual = grpc.grpc_object(
        BatchObject(collection="Test", properties={"value": value}, index=0)._to_internal()
    ).properties
    assert actual.non_ref_properties["value"] == value
    assert not actual.empty_list_props
    assert not actual.int_array_properties
    assert not actual.text_array_properties


@pytest.mark.parametrize("value", [b"", b"text", bytearray(b"text"), {1, 2}, iter([1, 2])])
def test_batch_unsupported_iterables_are_not_arrays(value: Any) -> None:
    grpc = _BatchGRPC(_ServerVersion(1, 40, 0), None, None)
    with pytest.raises(ValueError, match="Unexpected type"):
        grpc.grpc_object(
            BatchObject(collection="Test", properties={"value": value}, index=0)._to_internal()
        )


@pytest.mark.parametrize("sequence", [list, tuple, UserList])
def test_batch_object_array_sequences_validate_reserved_properties(sequence: Any) -> None:
    grpc = _BatchGRPC(_ServerVersion(1, 40, 0), None, None)
    with pytest.raises(WeaviateInsertInvalidPropertyError):
        grpc.grpc_object(
            BatchObject(
                collection="Test", properties={"objects": sequence([{"vector": [0.1]}])}, index=0
            )._to_internal()
        )
