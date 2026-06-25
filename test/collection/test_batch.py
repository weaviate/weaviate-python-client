import uuid

import pytest

from weaviate.collections.batch.base import (
    _DynamicBatching,
    _FixedSizeBatching,
    _RateLimitedBatching,
    _async_indexing_batch_params,
)
from weaviate.collections.batch.grpc_batch import _validate_props
from weaviate.collections.classes.batch import MAX_STORED_RESULTS, BatchObjectReturn
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


def test_async_indexing_preserves_rate_limit() -> None:
    # Async indexing has no server-side queue feedback, but a configured rate limit
    # must still be honoured rather than replaced by large fixed-size batches (#1542).
    requested = _RateLimitedBatching(requests_per_minute=100)

    mode, recommended_num_objects, concurrent_requests = _async_indexing_batch_params(
        requested, max_batch_size=1000
    )

    assert mode == requested
    assert concurrent_requests == 1
    assert recommended_num_objects == 100


def test_async_indexing_rate_limit_spans_multiple_batches() -> None:
    # A rate limit larger than the maximum batch size is split across several batches.
    requested = _RateLimitedBatching(requests_per_minute=3000)

    mode, recommended_num_objects, concurrent_requests = _async_indexing_batch_params(
        requested, max_batch_size=1000
    )

    assert mode == requested
    assert concurrent_requests == 4
    assert recommended_num_objects == 750


def test_async_indexing_dynamic_falls_back_to_fixed_size() -> None:
    # Without a configured rate limit, dynamic batching keeps its large-batch fallback.
    mode, recommended_num_objects, concurrent_requests = _async_indexing_batch_params(
        _DynamicBatching(), max_batch_size=1000
    )

    assert mode == _FixedSizeBatching(1000, 10)
    assert recommended_num_objects == 1000
    assert concurrent_requests == 10
