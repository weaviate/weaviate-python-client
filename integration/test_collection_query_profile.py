import re
from typing import Any

import pytest

from weaviate.collections import Collection
from weaviate.collections.classes.config import DataType, Property
from weaviate.collections.classes.data import DataObject
from weaviate.collections.classes.grpc import GroupBy, MetadataQuery
from weaviate.collections.classes.internal import SearchProfileReturn
from integration.conftest import CollectionFactory

GO_DURATION_RE = re.compile(r"[\d.]+(ns|µs|ms|s|m|h)")


def assert_go_duration(value: str, label: str = "") -> None:
    """Assert that a string looks like a Go duration (e.g. '1.234ms', '5.458µs')."""
    assert GO_DURATION_RE.fullmatch(value), (
        f"Expected Go duration format for {label!r}, got {value!r}"
    )


def assert_common_profile(profile: SearchProfileReturn) -> None:
    """Assertions shared by every search profile regardless of type."""
    assert len(profile.details) > 0, "Profile details should not be empty"
    assert "total_took" in profile.details
    assert_go_duration(profile.details["total_took"], "total_took")
    for key, value in profile.details.items():
        assert isinstance(key, str) and key != ""
        assert isinstance(value, str) and value != ""


def _create_and_populate(collection_factory: CollectionFactory) -> Collection[Any, Any]:
    collection = collection_factory(
        properties=[Property(name="text", data_type=DataType.TEXT)],
    )
    if collection._connection._weaviate_version.is_lower_than(1, 36, 9):
        pytest.skip("Query profiling requires Weaviate >= 1.36.9")
    collection.data.insert_many(
        [
            DataObject(properties={"text": "hello world"}, vector=[1.0, 0.0, 0.0]),
            DataObject(properties={"text": "goodbye world"}, vector=[0.0, 1.0, 0.0]),
            DataObject(properties={"text": "foo bar baz"}, vector=[0.0, 0.0, 1.0]),
        ]
    )
    return collection


def test_fetch_objects_with_query_profile(collection_factory: CollectionFactory) -> None:
    """Test that query profiling works with fetch_objects (object lookup)."""
    collection = _create_and_populate(collection_factory)
    result = collection.query.fetch_objects(
        return_metadata=MetadataQuery(query_profile=True),
    )
    assert len(result.objects) == 3
    assert result.query_profile is not None
    assert len(result.query_profile.shards) > 0

    shard = result.query_profile.shards[0]
    assert shard.name != ""
    assert shard.node != ""

    assert "object" in shard.searches
    assert_common_profile(shard.searches["object"])


def test_near_vector_with_query_profile(collection_factory: CollectionFactory) -> None:
    """Test that query profiling works with near_vector search."""
    collection = _create_and_populate(collection_factory)
    result = collection.query.near_vector(
        near_vector=[1.0, 0.0, 0.0],
        return_metadata=MetadataQuery(query_profile=True, distance=True),
        limit=2,
    )
    assert len(result.objects) == 2
    assert result.query_profile is not None
    assert len(result.query_profile.shards) > 0

    shard = result.query_profile.shards[0]
    assert "vector" in shard.searches
    vector_profile = shard.searches["vector"]
    assert_common_profile(vector_profile)

    assert "vector_search_took" in vector_profile.details
    assert_go_duration(vector_profile.details["vector_search_took"], "vector_search_took")

    assert "hnsw_flat_search" in vector_profile.details
    assert vector_profile.details["hnsw_flat_search"] in ("true", "false")

    layer_keys = [k for k in vector_profile.details if k.startswith("knn_search_layer_")]
    assert len(layer_keys) > 0, "Expected at least one knn_search_layer_*_took key"
    for k in layer_keys:
        assert_go_duration(vector_profile.details[k], k)

    assert "objects_took" in vector_profile.details
    assert_go_duration(vector_profile.details["objects_took"], "objects_took")


def test_bm25_with_query_profile(collection_factory: CollectionFactory) -> None:
    """Test that query profiling works with BM25 keyword search."""
    collection = _create_and_populate(collection_factory)
    result = collection.query.bm25(
        query="hello",
        return_metadata=MetadataQuery(query_profile=True, score=True),
    )
    assert result.query_profile is not None
    assert len(result.query_profile.shards) > 0

    shard = result.query_profile.shards[0]
    assert "keyword" in shard.searches
    keyword_profile = shard.searches["keyword"]
    assert_common_profile(keyword_profile)

    assert "kwd_method" in keyword_profile.details
    assert keyword_profile.details["kwd_method"] != ""

    assert "kwd_time" in keyword_profile.details
    assert_go_duration(keyword_profile.details["kwd_time"], "kwd_time")

    assert "kwd_1_tok_time" in keyword_profile.details
    assert_go_duration(keyword_profile.details["kwd_1_tok_time"], "kwd_1_tok_time")

    assert "kwd_6_res_count" in keyword_profile.details
    assert keyword_profile.details["kwd_6_res_count"].isdigit()
    assert int(keyword_profile.details["kwd_6_res_count"]) >= 0


def test_hybrid_with_query_profile(collection_factory: CollectionFactory) -> None:
    """Test that query profiling works with hybrid search (both vector and keyword)."""
    collection = _create_and_populate(collection_factory)
    result = collection.query.hybrid(
        query="hello",
        vector=[1.0, 0.0, 0.0],
        return_metadata=MetadataQuery(query_profile=True),
        limit=2,
    )
    assert result.query_profile is not None
    assert len(result.query_profile.shards) > 0

    shard = result.query_profile.shards[0]
    assert "vector" in shard.searches, "Hybrid should produce a 'vector' profile"
    assert "keyword" in shard.searches, "Hybrid should produce a 'keyword' profile"

    assert_common_profile(shard.searches["vector"])
    assert "vector_search_took" in shard.searches["vector"].details

    assert_common_profile(shard.searches["keyword"])
    assert "kwd_method" in shard.searches["keyword"].details


def test_near_vector_group_by_with_query_profile(
    collection_factory: CollectionFactory,
) -> None:
    """Test that query profiling works with group_by."""
    collection = _create_and_populate(collection_factory)
    result = collection.query.near_vector(
        near_vector=[1.0, 0.0, 0.0],
        return_metadata=MetadataQuery(query_profile=True),
        group_by=GroupBy(prop="text", objects_per_group=1, number_of_groups=3),
    )
    assert result.query_profile is not None
    assert len(result.query_profile.shards) > 0

    shard = result.query_profile.shards[0]
    assert "vector" in shard.searches
    assert_common_profile(shard.searches["vector"])


def test_no_query_profile_when_not_requested(
    collection_factory: CollectionFactory,
) -> None:
    """Test that query_profile is None when not requested."""
    collection = _create_and_populate(collection_factory)
    result = collection.query.fetch_objects(
        return_metadata=MetadataQuery(distance=True),
    )
    assert result.query_profile is None


def test_query_profile_with_metadata_list(
    collection_factory: CollectionFactory,
) -> None:
    """Test that query profiling works when using list-style metadata."""
    collection = _create_and_populate(collection_factory)
    result = collection.query.near_vector(
        near_vector=[1.0, 0.0, 0.0],
        return_metadata=["query_profile", "distance"],
        limit=2,
    )
    assert result.query_profile is not None
    assert len(result.query_profile.shards) > 0

    shard = result.query_profile.shards[0]
    assert "vector" in shard.searches
    assert_common_profile(shard.searches["vector"])


def test_query_profile_details_are_strings(
    collection_factory: CollectionFactory,
) -> None:
    """Test that all detail keys and values are non-empty strings."""
    collection = _create_and_populate(collection_factory)
    result = collection.query.near_vector(
        near_vector=[1.0, 0.0, 0.0],
        return_metadata=MetadataQuery(query_profile=True),
        limit=1,
    )
    assert result.query_profile is not None
    for shard in result.query_profile.shards:
        assert len(shard.searches) > 0, "Shard should have at least one search profile"
        for search_type, profile in shard.searches.items():
            assert isinstance(search_type, str) and search_type != ""
            assert len(profile.details) > 0
            for key, value in profile.details.items():
                assert isinstance(key, str) and key != ""
                assert isinstance(value, str) and value != ""
