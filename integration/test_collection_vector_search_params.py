"""Per-request vector search params via ``vector_search_params`` (Weaviate 1.42+).

The client's job is to deliver the option to the server unchanged, request-wide or per target
vector; the index semantics (flooring at ``k``, the ``HNSW_MAX_SEARCH_EF`` / ``HFRESH_MAX_SEARCH_PROBE``
caps, target-name checks, the bm25 rejection) are the server's and are only probed here as far as
they prove the fields arrived.
"""

import pytest

from integration.conftest import CollectionFactory
from weaviate.classes.config import VectorFilterStrategy
from weaviate.classes.query import Filter, HybridVector, VectorSearchParams
from weaviate.collections.classes.config import Configure, DataType, Property
from weaviate.collections.classes.data import DataObject
from weaviate.exceptions import WeaviateQueryError

_MIN_VERSION = (1, 42, 0)


def _skip_if_unsupported(collection_factory: CollectionFactory) -> None:
    # Gate on a throwaway collection before creating the real one: older servers reject some of
    # the index configs used here (hfresh is unknown before 1.35 and experimental-only in 1.35),
    # so checking the version after creation would turn a skip into a failure.
    dummy = collection_factory("dummy")
    if dummy._connection._weaviate_version.is_lower_than(*_MIN_VERSION):
        pytest.skip("vector_search_params requires Weaviate >= 1.42.0")


def _hnsw_collection(collection_factory: CollectionFactory, n: int = 50):
    _skip_if_unsupported(collection_factory)
    collection = collection_factory(
        properties=[Property(name="text", data_type=DataType.TEXT)],
        vector_config=Configure.Vectors.self_provided(
            vector_index_config=Configure.VectorIndex.hnsw()
        ),
    )
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
    _skip_if_unsupported(collection_factory)
    collection = collection_factory(
        properties=[Property(name="name", data_type=DataType.TEXT)],
        vector_config=Configure.Vectors.text2vec_contextionary(vectorize_collection_name=False),
    )
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
    _skip_if_unsupported(collection_factory)
    collection = collection_factory(
        properties=[Property(name="text", data_type=DataType.TEXT)],
        vector_config=Configure.Vectors.self_provided(
            vector_index_config=Configure.VectorIndex.flat()
        ),
    )
    collection.data.insert_many(
        [DataObject(properties={"text": str(i)}, vector=[1.0, float(i)]) for i in range(5)]
    )
    res = collection.query.near_vector(
        [1.0, 0.0], limit=2, vector_search_params=VectorSearchParams(ef=7)
    )
    assert len(res.objects) == 2


# --- all knobs, per index type --------------------------------------------------------------


@pytest.mark.parametrize("strategy", list(VectorFilterStrategy))
def test_filter_strategy_with_filter_matches_default(
    collection_factory: CollectionFactory, strategy: VectorFilterStrategy
) -> None:
    collection = _hnsw_collection(collection_factory)
    filters = Filter.by_property("text").like("obj-1*")

    baseline = collection.query.near_vector([1.0, 0.5, 3.0], limit=5, filters=filters).objects
    tuned = collection.query.near_vector(
        [1.0, 0.5, 3.0],
        limit=5,
        filters=filters,
        vector_search_params=VectorSearchParams.hnsw(filter_strategy=strategy),
    ).objects

    # 11 of 50 objects match the filter; any strategy on a 50-node graph is exhaustive.
    assert len(tuned) == 5
    assert {o.uuid for o in tuned} == {o.uuid for o in baseline}
    assert all(o.properties["text"].startswith("obj-1") for o in tuned)


def test_hnsw_ignores_search_probe(collection_factory: CollectionFactory) -> None:
    collection = _hnsw_collection(collection_factory)
    res = collection.query.near_vector(
        [1.0, 0.5, 3.0], limit=3, vector_search_params=VectorSearchParams.hfresh(search_probe=1)
    )
    assert len(res.objects) == 3


def _hfresh_collection(collection_factory: CollectionFactory, n: int = 50):
    _skip_if_unsupported(collection_factory)
    collection = collection_factory(
        properties=[Property(name="text", data_type=DataType.TEXT)],
        vector_config=Configure.Vectors.self_provided(
            vector_index_config=Configure.VectorIndex.hfresh()
        ),
    )
    collection.data.insert_many(
        [
            DataObject(properties={"text": f"obj-{i}"}, vector=[1.0, float(i) / n, float(i % 7)])
            for i in range(n)
        ]
    )
    return collection


def test_hfresh_search_probe_below_limit_is_floored_by_server(
    collection_factory: CollectionFactory,
) -> None:
    collection = _hfresh_collection(collection_factory)
    limit = 10
    baseline = collection.query.near_vector([1.0, 0.5, 3.0], limit=limit).objects
    tuned = collection.query.near_vector(
        [1.0, 0.5, 3.0],
        limit=limit,
        vector_search_params=VectorSearchParams.hfresh(search_probe=1),
    ).objects
    # The server applies max(search_probe, k), so a tiny probe never truncates the result set.
    assert len(tuned) == limit
    assert {o.uuid for o in tuned} == {o.uuid for o in baseline}


def test_hfresh_search_probe_above_server_cap_is_rejected(
    collection_factory: CollectionFactory,
) -> None:
    collection = _hfresh_collection(collection_factory, n=5)
    with pytest.raises(WeaviateQueryError) as exc:
        collection.query.near_vector(
            [1.0, 0.0, 0.0], vector_search_params=VectorSearchParams.hfresh(search_probe=10_000_001)
        )
    assert "HFRESH_MAX_SEARCH_PROBE" in str(exc.value)


def test_hfresh_ignores_hnsw_knobs(collection_factory: CollectionFactory) -> None:
    collection = _hfresh_collection(collection_factory)
    res = collection.query.near_vector(
        [1.0, 0.5, 3.0],
        limit=3,
        vector_search_params=VectorSearchParams.hnsw(
            ef=1, filter_strategy=VectorFilterStrategy.ACORN
        ),
    )
    assert len(res.objects) == 3


# --- per-target mapping ----------------------------------------------------------------------


def _multi_vector_collection(collection_factory: CollectionFactory, n: int = 50):
    _skip_if_unsupported(collection_factory)
    collection = collection_factory(
        properties=[Property(name="text", data_type=DataType.TEXT)],
        vector_config=[
            Configure.Vectors.self_provided(
                name="first", vector_index_config=Configure.VectorIndex.hnsw()
            ),
            Configure.Vectors.self_provided(
                name="second", vector_index_config=Configure.VectorIndex.hnsw()
            ),
        ],
    )
    collection.data.insert_many(
        [
            DataObject(
                properties={"text": f"obj-{i}"},
                vector={
                    "first": [1.0, float(i) / n, float(i % 7)],
                    "second": [float(i % 3), 1.0, float(n - i) / n],
                },
            )
            for i in range(n)
        ]
    )
    return collection


def test_per_target_params_on_multi_target_search(collection_factory: CollectionFactory) -> None:
    collection = _multi_vector_collection(collection_factory)
    limit = 10
    query = {"first": [1.0, 0.5, 3.0], "second": [1.0, 1.0, 0.5]}

    baseline = collection.query.near_vector(
        query, target_vector=["first", "second"], limit=limit
    ).objects
    tuned = collection.query.near_vector(
        query,
        target_vector=["first", "second"],
        limit=limit,
        vector_search_params={
            "first": VectorSearchParams.hnsw(ef=1),
            "second": VectorSearchParams.hnsw(
                ef=512, filter_strategy=VectorFilterStrategy.SWEEPING
            ),
        },
    ).objects

    assert len(tuned) == limit
    assert {o.uuid for o in tuned} == {o.uuid for o in baseline}


def test_per_target_params_for_a_subset_of_targets(collection_factory: CollectionFactory) -> None:
    # Targets without an entry keep the collection config; only the named one is tuned.
    collection = _multi_vector_collection(collection_factory)
    res = collection.query.near_vector(
        {"first": [1.0, 0.5, 3.0], "second": [1.0, 1.0, 0.5]},
        target_vector=["first", "second"],
        limit=5,
        vector_search_params={"second": VectorSearchParams.hnsw(ef=64)},
    )
    assert len(res.objects) == 5


def test_per_target_params_on_single_named_vector(collection_factory: CollectionFactory) -> None:
    collection = _multi_vector_collection(collection_factory)
    baseline = collection.query.near_vector([1.0, 0.5, 3.0], target_vector="first", limit=5).objects
    tuned = collection.query.near_vector(
        [1.0, 0.5, 3.0],
        target_vector="first",
        limit=5,
        vector_search_params={"first": VectorSearchParams.hnsw(ef=1)},
    ).objects
    assert {o.uuid for o in tuned} == {o.uuid for o in baseline}


def test_per_target_params_on_hybrid(collection_factory: CollectionFactory) -> None:
    collection = _multi_vector_collection(collection_factory)
    res = collection.query.hybrid(
        "obj",
        vector=HybridVector.near_vector([1.0, 0.5, 3.0]),
        target_vector="first",
        alpha=0.5,
        limit=5,
        vector_search_params={"first": VectorSearchParams.hnsw(ef=64)},
    )
    assert len(res.objects) == 5


def test_unknown_target_is_rejected_by_server(collection_factory: CollectionFactory) -> None:
    # Target names are deliberately not validated client-side so the error text has one source.
    collection = _multi_vector_collection(collection_factory, n=5)
    with pytest.raises(WeaviateQueryError) as exc:
        collection.query.near_vector(
            [1.0, 0.5, 3.0],
            target_vector="first",
            vector_search_params={"nope": VectorSearchParams.hnsw(ef=8)},
        )
    assert "nope" in str(exc.value)


def test_target_not_in_request_is_rejected_by_server(
    collection_factory: CollectionFactory,
) -> None:
    # "second" exists on the collection but is not searched by this request.
    collection = _multi_vector_collection(collection_factory, n=5)
    with pytest.raises(WeaviateQueryError) as exc:
        collection.query.near_vector(
            [1.0, 0.5, 3.0],
            target_vector="first",
            vector_search_params={"second": VectorSearchParams.hnsw(ef=8)},
        )
    assert "second" in str(exc.value)


def test_per_target_params_rejected_on_legacy_collection(
    collection_factory: CollectionFactory,
) -> None:
    # A legacy single-vector collection has no target names to address.
    _skip_if_unsupported(collection_factory)
    collection = collection_factory(
        properties=[Property(name="text", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    collection.data.insert_many(
        [DataObject(properties={"text": str(i)}, vector=[1.0, float(i)]) for i in range(5)]
    )
    # The request-wide form still works on a legacy collection.
    assert (
        len(
            collection.query.near_vector(
                [1.0, 0.0], limit=2, vector_search_params=VectorSearchParams.hnsw(ef=16)
            ).objects
        )
        == 2
    )
    with pytest.raises(WeaviateQueryError):
        collection.query.near_vector(
            [1.0, 0.0], limit=2, vector_search_params={"default": VectorSearchParams.hnsw(ef=16)}
        )
