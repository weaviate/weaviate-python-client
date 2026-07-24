"""Integration tests for hybrid search + MMR diversity selection.

``DiversitySelection`` passed inside ``HybridVector.near_vector`` /
``HybridVector.near_text`` is applied by the server as a post-fusion MMR pass
(Weaviate >= 1.39.0). These tests assert that ``balance=0`` (pure diversity)
produces a different ordering than ``balance=1`` (pure relevance), and that
``mmr.limit`` caps the result count.

The equivalent ``near_vector`` behaviour is covered in
``test_collection_diversity.py``.
"""

import pytest

from integration.conftest import CollectionFactory
from weaviate.classes.query import Diversity, HybridVector
from weaviate.collections.classes.config import Configure, DataType, Property
from weaviate.collections.classes.data import DataObject

MIN_VERSION = (1, 38, 6)


def _skip_if_unsupported(collection) -> None:
    if collection._connection._weaviate_version.is_lower_than(*MIN_VERSION):
        pytest.skip("Hybrid diversity selection requires Weaviate >= 1.38.6")


def _create_clustered_collection(collection_factory: CollectionFactory):
    """Create a collection with 3 tight clusters (a, b, c) of vectors in 3D."""
    collection = collection_factory(
        properties=[Property(name="text", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    _skip_if_unsupported(collection)
    collection.data.insert_many(
        [
            DataObject(properties={"text": "a1"}, vector=[1.0, 0.0, 0.0]),
            DataObject(properties={"text": "a2"}, vector=[0.95, 0.05, 0.0]),
            DataObject(properties={"text": "a3"}, vector=[0.9, 0.1, 0.0]),
            DataObject(properties={"text": "b1"}, vector=[0.0, 1.0, 0.0]),
            DataObject(properties={"text": "b2"}, vector=[0.05, 0.95, 0.0]),
            DataObject(properties={"text": "c1"}, vector=[0.0, 0.0, 1.0]),
        ]
    )
    return collection


def _create_large_collection(collection_factory: CollectionFactory, n_items: int = 50):
    """Create a collection with enough items (>25) that a small mmr.limit is distinguishable from the server's default limit."""
    collection = collection_factory(
        properties=[Property(name="text", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    _skip_if_unsupported(collection)
    collection.data.insert_many(
        [
            DataObject(properties={"text": f"t{i}"}, vector=[1.0 - 0.001 * i, 0.0, 0.0])
            for i in range(n_items)
        ]
    )
    return collection


def test_hybrid_near_vector_balance_0_differs_from_balance_1(
    collection_factory: CollectionFactory,
) -> None:
    """Hybrid near-vector: balance=0 (diversity) must reorder vs balance=1 (relevance)."""
    collection = _create_clustered_collection(collection_factory)
    balance_0 = collection.query.hybrid(
        query=None,
        vector=HybridVector.near_vector(
            vector=[1.0, 0.0, 0.0],
            diversity_selection=Diversity.mmr(limit=3, balance=0.0),
        ),
        limit=3,
    ).objects
    balance_1 = collection.query.hybrid(
        query=None,
        vector=HybridVector.near_vector(
            vector=[1.0, 0.0, 0.0],
            diversity_selection=Diversity.mmr(limit=3, balance=1.0),
        ),
        limit=3,
    ).objects
    assert [o.uuid for o in balance_0] != [o.uuid for o in balance_1]


def test_hybrid_near_vector_balance_1_matches_baseline(
    collection_factory: CollectionFactory,
) -> None:
    """Hybrid near-vector with MMR balance=1 (pure relevance) matches the plain baseline."""
    collection = _create_clustered_collection(collection_factory)
    baseline = collection.query.hybrid(
        query=None,
        vector=HybridVector.near_vector(vector=[1.0, 0.0, 0.0]),
        limit=3,
    ).objects
    mmr_balance_1 = collection.query.hybrid(
        query=None,
        vector=HybridVector.near_vector(
            vector=[1.0, 0.0, 0.0],
            diversity_selection=Diversity.mmr(limit=3, balance=1.0),
        ),
        limit=3,
    ).objects
    assert [o.uuid for o in baseline] == [o.uuid for o in mmr_balance_1]


def test_hybrid_alpha_1_balance_0_differs_from_balance_1(
    collection_factory: CollectionFactory,
) -> None:
    """Hybrid with explicit alpha=1.0 (pure vector) applies MMR like near_vector."""
    collection = _create_clustered_collection(collection_factory)
    balance_0 = collection.query.hybrid(
        query="irrelevant",
        alpha=1.0,
        vector=HybridVector.near_vector(
            vector=[1.0, 0.0, 0.0],
            diversity_selection=Diversity.mmr(limit=3, balance=0.0),
        ),
        limit=3,
    ).objects
    balance_1 = collection.query.hybrid(
        query="irrelevant",
        alpha=1.0,
        vector=HybridVector.near_vector(
            vector=[1.0, 0.0, 0.0],
            diversity_selection=Diversity.mmr(limit=3, balance=1.0),
        ),
        limit=3,
    ).objects
    assert [o.uuid for o in balance_0] != [o.uuid for o in balance_1]


def test_hybrid_respects_mmr_limit(
    collection_factory: CollectionFactory,
) -> None:
    """Hybrid respects mmr.limit as the result-count cap when no outer limit is set."""
    mmr_limit = 5
    collection = _create_large_collection(collection_factory, n_items=50)

    result = collection.query.hybrid(
        query=None,
        vector=HybridVector.near_vector(
            vector=[1.0, 0.0, 0.0],
            diversity_selection=Diversity.mmr(limit=mmr_limit, balance=0.5),
        ),
    ).objects
    assert len(result) == mmr_limit
