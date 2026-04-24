"""Regression tests for hybrid search + MMR diversity selection.

Every test in this file is currently marked ``xfail(strict=True)``: the client
correctly wires ``DiversitySelection`` into the hybrid request (confirmed by
inspecting the serialized proto — ``Hybrid.near_vector.selection.mmr`` is
populated), but Weaviate's hybrid code path silently drops the field, so
``balance=0.0`` produces byte-identical results to ``balance=1.0``.

When server-side support lands, these tests will start to pass and pytest will
report XPASS, prompting removal of the ``xfail`` markers.

The equivalent ``near_vector`` behaviour (MMR ``balance=0`` differs from
``balance=1``) is already covered in ``test_collection_diversity.py`` and
passes today — it serves as the baseline proving the client-side wiring works.
"""

import pytest

from integration.conftest import CollectionFactory
from weaviate.classes.query import DiversitySelection, HybridVector
from weaviate.collections.classes.config import Configure, DataType, Property
from weaviate.collections.classes.data import DataObject

XFAIL_REASON = (
    "Hybrid sub-query diversity selection is not yet honored server-side "
    "(as of Weaviate 1.37.1). The client sends Hybrid.near_vector.selection in the "
    "proto request, but the server silently drops it in the hybrid code path: "
    "balance=0.0 returns the same ordering as balance=1.0. "
    "Remove xfail when server support lands."
)


def _create_clustered_collection(collection_factory: CollectionFactory):
    """Create a collection with 3 tight clusters (a, b, c) of vectors in 3D."""
    collection = collection_factory(
        properties=[Property(name="text", data_type=DataType.TEXT)],
        vectorizer_config=Configure.Vectorizer.none(),
    )
    if collection._connection._weaviate_version.is_lower_than(1, 37, 0):
        pytest.skip("Diversity selection requires Weaviate >= 1.37.0")
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
    if collection._connection._weaviate_version.is_lower_than(1, 37, 0):
        pytest.skip("Diversity selection requires Weaviate >= 1.37.0")
    collection.data.insert_many(
        [
            DataObject(properties={"text": f"t{i}"}, vector=[1.0 - 0.001 * i, 0.0, 0.0])
            for i in range(n_items)
        ]
    )
    return collection


@pytest.mark.xfail(reason=XFAIL_REASON, strict=True)
def test_hybrid_query_none_balance_0_differs_from_balance_1(
    collection_factory: CollectionFactory,
) -> None:
    """Test hybrid(query=None) — the vector-only hybrid path should apply MMR.

    When ``query`` is None the client sets ``alpha=1`` internally, so the
    search is purely vector-based. The result should therefore match a
    standalone ``near_vector`` query: ``balance=0`` must produce a different
    ordering than ``balance=1``.
    """
    collection = _create_clustered_collection(collection_factory)
    balance_0 = collection.query.hybrid(
        query=None,
        vector=HybridVector.near_vector(
            vector=[1.0, 0.0, 0.0],
            diversity_selection=DiversitySelection.mmr(limit=3, balance=0.0),
        ),
        limit=3,
    ).objects
    balance_1 = collection.query.hybrid(
        query=None,
        vector=HybridVector.near_vector(
            vector=[1.0, 0.0, 0.0],
            diversity_selection=DiversitySelection.mmr(limit=3, balance=1.0),
        ),
        limit=3,
    ).objects
    assert [o.uuid for o in balance_0] != [o.uuid for o in balance_1]


@pytest.mark.xfail(
    reason=(
        "mmr.limit is ignored by Weaviate's hybrid code path (as of 1.37.1). When no "
        "outer query limit is set, hybrid returns the server's default (25 items) "
        "regardless of mmr.limit, whereas near_vector respects mmr.limit. "
        "Remove xfail when server support lands."
    ),
    strict=True,
)
def test_hybrid_respects_mmr_limit(
    collection_factory: CollectionFactory,
) -> None:
    """Test hybrid respects ``mmr.limit`` as the result-count cap when no outer limit is set.

    Collection has 50 items (> default server limit of 25) and no outer
    ``limit`` is passed. ``near_vector`` correctly returns ``mmr.limit`` items;
    ``hybrid`` returns the server default (25) instead of ``mmr.limit=5``.
    """
    mmr_limit = 5
    collection = _create_large_collection(collection_factory, n_items=50)

    result = collection.query.hybrid(
        query=None,
        vector=HybridVector.near_vector(
            vector=[1.0, 0.0, 0.0],
            diversity_selection=DiversitySelection.mmr(limit=mmr_limit, balance=0.5),
        ),
    ).objects
    assert len(result) == mmr_limit


@pytest.mark.xfail(reason=XFAIL_REASON, strict=True)
def test_hybrid_alpha_1_balance_0_differs_from_balance_1(
    collection_factory: CollectionFactory,
) -> None:
    """Test hybrid with explicit alpha=1.0 (pure vector) — should apply MMR.

    ``alpha=1.0`` disables the keyword/BM25 component, leaving only the vector
    sub-query. The keyword query string is therefore effectively ignored and
    MMR should apply the same way it does for standalone ``near_vector``.
    """
    collection = _create_clustered_collection(collection_factory)
    balance_0 = collection.query.hybrid(
        query="irrelevant",
        alpha=1.0,
        vector=HybridVector.near_vector(
            vector=[1.0, 0.0, 0.0],
            diversity_selection=DiversitySelection.mmr(limit=3, balance=0.0),
        ),
        limit=3,
    ).objects
    balance_1 = collection.query.hybrid(
        query="irrelevant",
        alpha=1.0,
        vector=HybridVector.near_vector(
            vector=[1.0, 0.0, 0.0],
            diversity_selection=DiversitySelection.mmr(limit=3, balance=1.0),
        ),
        limit=3,
    ).objects
    assert [o.uuid for o in balance_0] != [o.uuid for o in balance_1]
