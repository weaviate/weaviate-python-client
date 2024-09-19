import pytest
import weaviate
from weaviate.exceptions import WeaviateTimeoutError, WeaviateQueryError


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
