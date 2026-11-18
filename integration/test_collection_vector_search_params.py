"""Per-request HNSW ``ef`` via ``vector_search_params`` (Weaviate 1.41+).

The client's job is to deliver the option to the server unchanged; the HNSW semantics (flooring
at ``k``, the ``HNSW_MAX_SEARCH_EF`` cap, the bm25 rejection) are the server's and are only probed
here as far as they prove the field arrived.
"""

import pytest

from integration.conftest import CollectionFactory
from weaviate.classes.query import HybridVector, VectorSearchParams
from weaviate.collections.classes.config import Configure, DataType, Property
from weaviate.collections.classes.data import DataObject
from weaviate.exceptions import WeaviateQueryError

_MIN_VERSION = (1, 41, 0)


def _hnsw_collection(collection_factory: CollectionFactory, n: int = 50):
    collection = collection_factory(
        properties=[Property(name="text", data_type=DataType.TEXT)],
        vector_config=Configure.Vectors.self_provided(
            vector_index_config=Configure.VectorIndex.hnsw()
        ),
    )
    if collection._connection._weaviate_version.is_lower_than(*_MIN_VERSION):
        pytest.skip("vector_search_params requires Weaviate >= 1.41.0")
    collection.data.insert_many(
        [
            DataObject(properties={"text": f"obj-{i}"}, vector=[1.0, float(i) / n, float(i % 7)])
            for i in range(n)
        ]
    )
    return collection


def test_near_vector_ef_below_limit_is_floored_by_server(
    collection_factory: CollectionFactory,
) -> None:
    collection = _hnsw_collection(collection_factory)
    limit = 10

    baseline = collection.query.near_vector([1.0, 0.5, 3.0], limit=limit).objects
    with_ef = collection.query.near_vector(
        [1.0, 0.5, 3.0], limit=limit, vector_search_params=VectorSearchParams(ef=1)
    ).objects

    # The server applies max(ef, k), so a tiny ef never truncates the result set.
    assert len(with_ef) == limit
    # On a 50-object graph ef >= k is exhaustive, so the sets agree with the default-ef search.
    assert {o.uuid for o in with_ef} == {o.uuid for o in baseline}


def test_near_vector_high_ef_matches_default(collection_factory: CollectionFactory) -> None:
    collection = _hnsw_collection(collection_factory)
    baseline = collection.query.near_vector([1.0, 0.2, 1.0], limit=5).objects
    with_ef = collection.query.near_vector(
        [1.0, 0.2, 1.0], limit=5, vector_search_params=VectorSearchParams(ef=512)
    ).objects
    assert [o.uuid for o in with_ef] == [o.uuid for o in baseline]


def test_near_object_accepts_vector_search_params(collection_factory: CollectionFactory) -> None:
    collection = _hnsw_collection(collection_factory)
    anchor = next(iter(collection.query.fetch_objects(limit=1).objects)).uuid
    res = collection.query.near_object(
        anchor, limit=3, vector_search_params=VectorSearchParams(ef=64)
    )
    assert len(res.objects) == 3
    assert res.objects[0].uuid == anchor


def test_hybrid_accepts_vector_search_params(collection_factory: CollectionFactory) -> None:
    collection = _hnsw_collection(collection_factory)
    res = collection.query.hybrid(
        "obj",
        vector=HybridVector.near_vector([1.0, 0.5, 3.0]),
        alpha=0.5,
        limit=5,
        vector_search_params=VectorSearchParams(ef=64),
    )
    assert len(res.objects) == 5


def test_near_text_accepts_vector_search_params(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="name", data_type=DataType.TEXT)],
        vector_config=Configure.Vectors.text2vec_contextionary(vectorize_collection_name=False),
    )
    if collection._connection._weaviate_version.is_lower_than(*_MIN_VERSION):
        pytest.skip("vector_search_params requires Weaviate >= 1.41.0")
    for name in ["banana", "apple", "orange", "car", "truck", "bike"]:
        collection.data.insert({"name": name})

    res = collection.query.near_text(
        "fruit", limit=3, vector_search_params=VectorSearchParams(ef=64)
    )
    assert len(res.objects) == 3


def test_ef_above_server_cap_is_rejected(collection_factory: CollectionFactory) -> None:
    # HNSW_MAX_SEARCH_EF defaults to QUERY_MAXIMUM_RESULTS (10000); the server answers
    # InvalidArgument, which the client surfaces as a query error rather than truncating.
    collection = _hnsw_collection(collection_factory, n=5)
    with pytest.raises(WeaviateQueryError) as exc:
        collection.query.near_vector(
            [1.0, 0.0, 0.0], vector_search_params=VectorSearchParams(ef=10_000_001)
        )
    assert "HNSW_MAX_SEARCH_EF" in str(exc.value)


def test_flat_index_ignores_vector_search_params(collection_factory: CollectionFactory) -> None:
    collection = collection_factory(
        properties=[Property(name="text", data_type=DataType.TEXT)],
        vector_config=Configure.Vectors.self_provided(
            vector_index_config=Configure.VectorIndex.flat()
        ),
    )
    if collection._connection._weaviate_version.is_lower_than(*_MIN_VERSION):
        pytest.skip("vector_search_params requires Weaviate >= 1.41.0")
    collection.data.insert_many(
        [DataObject(properties={"text": str(i)}, vector=[1.0, float(i)]) for i in range(5)]
    )
    res = collection.query.near_vector(
        [1.0, 0.0], limit=2, vector_search_params=VectorSearchParams(ef=7)
    )
    assert len(res.objects) == 2
