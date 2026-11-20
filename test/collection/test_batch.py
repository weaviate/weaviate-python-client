import struct
import uuid
from decimal import Decimal
from typing import Any, Dict

import numpy as np
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
    _BatchObject,
)
from weaviate.exceptions import WeaviateInsertInvalidPropertyError, WeaviateInvalidInputError
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


def _grpc_object(properties: Dict[str, Any]) -> batch_pb2.BatchObject:
    grpc = _BatchGRPC(_ServerVersion(1, 40, 0), None, None)
    return grpc.grpc_object(
        _BatchObject(
            collection="Test",
            properties=properties,
            references=None,
            uuid=None,
            vector=None,
            tenant=None,
            index=0,
        )
    )


def _number_array(obj: batch_pb2.BatchObject, name: str) -> list:
    for prop in obj.properties.number_array_properties:
        if prop.prop_name == name:
            return list(struct.unpack(f"{len(prop.values_bytes) // 8}d", prop.values_bytes))
    raise AssertionError(f"no number array named {name}")


@pytest.mark.parametrize(
    "value",
    [Decimal("9.99"), np.float32(9.99)],
)
def test_grpc_object_converts_scalar_numbers(value: Any) -> None:
    obj = _grpc_object({"price": value})
    assert obj.properties.non_ref_properties["price"] == pytest.approx(9.99, rel=1e-6)


def test_grpc_object_converts_numpy_int() -> None:
    obj = _grpc_object({"count": np.int64(3)})
    assert obj.properties.non_ref_properties["count"] == 3


def test_grpc_object_converts_nested_decimal() -> None:
    obj = _grpc_object({"item": {"price": Decimal("9.99")}})
    nested = obj.properties.object_properties[0]
    assert nested.prop_name == "item"
    assert nested.value.non_ref_properties["price"] == 9.99


@pytest.mark.parametrize(
    "value",
    [[Decimal("1.5"), 2.5], [1.5, Decimal("2.5")], [Decimal("1.5"), Decimal("2.5")]],
)
def test_grpc_object_converts_decimals_in_lists(value: Any) -> None:
    assert _number_array(_grpc_object({"prices": value}), "prices") == [1.5, 2.5]


def test_grpc_object_converts_numpy_ints_in_lists() -> None:
    obj = _grpc_object({"counts": [np.int64(1), np.int64(2)]})
    assert list(obj.properties.int_array_properties[0].values) == [1, 2]


def test_grpc_object_accepts_tuple_of_uuids() -> None:
    obj = _grpc_object(
        {
            "ids": (
                uuid.UUID("11111111-1111-1111-1111-111111111111"),
                uuid.UUID("22222222-2222-2222-2222-222222222222"),
            )
        }
    )
    values = obj.properties.non_ref_properties["ids"]
    assert list(values) == [
        "11111111-1111-1111-1111-111111111111",
        "22222222-2222-2222-2222-222222222222",
    ]


@pytest.mark.parametrize("value", [Decimal("NaN"), Decimal("1e400"), [1.5, Decimal("Infinity")]])
def test_grpc_object_raises_for_non_finite_numbers(value: Any) -> None:
    with pytest.raises(WeaviateInvalidInputError, match="non-finite"):
        _grpc_object({"price": value})


@pytest.mark.parametrize("value", [object(), {"inner": object()}, [object(), "a"]])
def test_grpc_object_raises_for_unsupported_types(value: Any) -> None:
    with pytest.raises(WeaviateInvalidInputError, match="Cannot serialize value of type"):
        _grpc_object({"value": value})
