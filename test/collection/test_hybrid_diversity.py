"""Unit tests: hybrid search wires diversity_selection into the gRPC request.

Hybrid diversity is a post-fusion, hybrid-level operation, so the top-level
``query.hybrid`` / ``generate.hybrid`` ``diversity_selection`` argument must
populate the top-level ``Hybrid.selection.mmr`` in the SearchRequest proto (not
the nested ``near_vector`` / ``near_text`` selection).
"""

from weaviate.collections.grpc.query import _QueryGRPC
from weaviate.classes.query import Diversity, HybridVector
from weaviate.util import _ServerVersion


_DEFAULT_VERSION = _ServerVersion(1, 38, 0)


def _builder(version: _ServerVersion = _DEFAULT_VERSION) -> _QueryGRPC:
    return _QueryGRPC(
        weaviate_version=version,
        name="Dummy",
        tenant=None,
        consistency_level=None,
        validate_arguments=True,
        uses_125_api=True,
        uses_127_api=True,
    )


def test_hybrid_near_vector_sets_top_level_selection() -> None:
    req = _builder().hybrid(
        query=None,
        vector=HybridVector.near_vector(vector=[1.0, 0.0, 0.0]),
        diversity_selection=Diversity.mmr(limit=7, balance=0.0),
        limit=7,
    )
    # Canonical location: top-level Hybrid.selection, not the nested near_vector.
    mmr = req.hybrid_search.selection.mmr
    assert mmr.limit == 7
    assert mmr.balance == 0.0
    assert not req.hybrid_search.near_vector.HasField("selection")


def test_hybrid_near_text_sets_top_level_selection() -> None:
    req = _builder().hybrid(
        query=None,
        vector=HybridVector.near_text(query="cats"),
        diversity_selection=Diversity.mmr(limit=3, balance=0.5),
        limit=3,
    )
    mmr = req.hybrid_search.selection.mmr
    assert mmr.limit == 3
    assert mmr.balance == 0.5
    assert not req.hybrid_search.near_text.HasField("selection")


def test_hybrid_without_selection_leaves_it_unset() -> None:
    req = _builder().hybrid(
        query=None,
        vector=HybridVector.near_vector(vector=[1.0, 0.0, 0.0]),
        limit=5,
    )
    assert not req.hybrid_search.HasField("selection")
