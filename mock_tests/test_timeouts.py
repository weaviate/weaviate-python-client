import pytest

import weaviate
from weaviate.exceptions import WeaviateQueryError, WeaviateTimeoutError

from .conftest import BATCH_INSERT_TIMEOUT, MockBatchDeadlineCaptureWeaviateService


def test_timeout_rest_query(timeouts_collection: weaviate.collections.Collection):
    with pytest.raises(WeaviateTimeoutError):
        timeouts_collection.config.get()


def test_timeout_rest_insert(timeouts_collection: weaviate.collections.Collection):
    with pytest.raises(WeaviateTimeoutError):
        timeouts_collection.data.insert(properties={"what": "ever"})


def test_timeout_grpc_query(timeouts_collection: weaviate.collections.Collection):
    with pytest.raises(WeaviateQueryError) as recwarn:
        timeouts_collection.query.fetch_objects()
        assert "DEADLINE_EXCEEDED" in str(recwarn)


def test_timeout_grpc_insert(timeouts_collection: weaviate.collections.Collection):
    with pytest.raises(WeaviateQueryError) as recwarn:
        timeouts_collection.data.insert_many([{"what": "ever"}])
        assert "DEADLINE_EXCEEDED" in str(recwarn)


def test_batch_fixed_size_deadline_uses_insert_timeout(
    batch_deadline_capture_collection: tuple[
        weaviate.collections.Collection, MockBatchDeadlineCaptureWeaviateService
    ],
):
    collection, service = batch_deadline_capture_collection
    with collection.batch.fixed_size(batch_size=1) as batch:
        batch.add_object({"what": "ever"})
    assert abs(service.captured_time_remaining - BATCH_INSERT_TIMEOUT) < 1


def test_batch_fixed_size_times_out_when_insert_exceeded(
    batch_slow_response_collection: weaviate.collections.Collection,
):
    with batch_slow_response_collection.batch.fixed_size(batch_size=1) as batch:
        batch.add_object({"what": "ever"})
    failed = batch_slow_response_collection.batch.failed_objects
    assert len(failed) == 1
    assert "Deadline Exceeded" in failed[0].message
