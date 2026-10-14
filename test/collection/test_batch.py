import uuid
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock

import pytest

from weaviate.collections.batch.base import (
    _BatchBase,
    _BatchDataWrapper,
    _DynamicBatching,
    _FixedSizeBatching,
    _RateLimitedBatching,
)
from weaviate.collections.batch.client import _BatchClientWrapper
from weaviate.collections.batch.collection import _BatchCollection, _BatchCollectionWrapper
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


def _batch_connection_mock() -> MagicMock:
    connection = MagicMock()
    connection._weaviate_version = _ServerVersion.from_string("1.36.0")
    connection._grpc_max_msg_size = None
    return connection


def test_client_batch_dynamic_does_not_discard_configured_rate_limit() -> None:
    wrapper = _BatchClientWrapper(
        connection=_batch_connection_mock(),
        config=MagicMock(),
        consistency_level=None,
    )
    wrapper._vectorizer_batching = True
    wrapper.rate_limit(requests_per_minute=100)
    assert isinstance(wrapper._batch_mode, _RateLimitedBatching)

    ctx = wrapper.dynamic()

    assert isinstance(wrapper._batch_mode, _RateLimitedBatching)
    assert wrapper._batch_mode.requests_per_minute == 100
    inner_batch = ctx._ContextManagerSync__current_batch
    assert isinstance(inner_batch._BatchBase__batching_mode, _RateLimitedBatching)
    assert inner_batch._BatchBase__batching_mode.requests_per_minute == 100
    assert inner_batch._BatchBase__recommended_num_objects == 100
    assert inner_batch._BatchBase__concurrent_requests == 1


def test_collection_batch_dynamic_does_not_discard_configured_rate_limit() -> None:
    wrapper = _BatchCollectionWrapper(
        connection=_batch_connection_mock(),
        consistency_level=None,
        name="Foo",
        tenant=None,
        config=MagicMock(),
        batch_client=_BatchCollection,
    )
    wrapper._vectorizer_batching = False
    wrapper.rate_limit(requests_per_minute=100)
    assert isinstance(wrapper._batch_mode, _RateLimitedBatching)

    ctx = wrapper.dynamic()

    assert isinstance(wrapper._batch_mode, _RateLimitedBatching)
    assert wrapper._batch_mode.requests_per_minute == 100
    inner_batch = ctx._ContextManagerSync__current_batch
    assert isinstance(inner_batch._BatchBase__batching_mode, _RateLimitedBatching)
    assert inner_batch._BatchBase__batching_mode.requests_per_minute == 100
    assert inner_batch._BatchBase__recommended_num_objects == 100
    assert inner_batch._BatchBase__concurrent_requests == 1


def test_async_indexing_fallback_does_not_override_rate_limited_mode() -> None:
    batch = _BatchBase(
        connection=_batch_connection_mock(),
        consistency_level=None,
        results=_BatchDataWrapper(),
        batch_mode=_RateLimitedBatching(requests_per_minute=100),
        executor=ThreadPoolExecutor(),
        vectorizer_batching=False,
    )
    cluster = MagicMock()
    # a node without "batchStats" is the async-indexing response shape
    cluster.get_nodes_status.return_value = [{}]
    batch._BatchBase__cluster = cluster

    batch._BatchBase__dynamic_batching()

    assert isinstance(batch._BatchBase__batching_mode, _RateLimitedBatching)
    assert batch._BatchBase__batching_mode.requests_per_minute == 100
    assert batch._BatchBase__recommended_num_objects == 100
    assert batch._BatchBase__concurrent_requests == 1


def test_async_indexing_fallback_still_replaces_plain_dynamic_mode() -> None:
    batch = _BatchBase(
        connection=_batch_connection_mock(),
        consistency_level=None,
        results=_BatchDataWrapper(),
        batch_mode=_DynamicBatching(),
        executor=ThreadPoolExecutor(),
        vectorizer_batching=False,
    )
    cluster = MagicMock()
    cluster.get_nodes_status.return_value = [{}]
    batch._BatchBase__cluster = cluster

    batch._BatchBase__dynamic_batching()

    assert isinstance(batch._BatchBase__batching_mode, _FixedSizeBatching)
    assert batch._BatchBase__batching_mode.batch_size == 1000
    assert batch._BatchBase__batching_mode.concurrent_requests == 10
    assert batch._BatchBase__recommended_num_objects == 1000
    assert batch._BatchBase__concurrent_requests == 10
