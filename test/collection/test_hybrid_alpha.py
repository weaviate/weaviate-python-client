"""Unit tests: hybrid search sends alpha in the field the server version understands.

Servers before 1.36.7 do not read ``Hybrid.use_alpha_param``: they take alpha from the
legacy ``Hybrid.alpha`` field (search also reads ``alpha_param`` when it is set, aggregate
does not). From 1.36.7 the server reads ``alpha_param`` when ``use_alpha_param`` is set and
applies its own default when no alpha is given.
"""

import pytest

from weaviate.collections.grpc.aggregate import _AggregateGRPC
from weaviate.collections.grpc.query import _QueryGRPC
from weaviate.proto.v1 import base_search_pb2
from weaviate.util import _ServerVersion

_BEFORE_1_36_7 = [_ServerVersion(1, 36, 5), _ServerVersion(1, 36, 6)]
_FROM_1_36_7 = [_ServerVersion(1, 36, 7), _ServerVersion(1, 37, 0)]


def _query(version: _ServerVersion) -> _QueryGRPC:
    return _QueryGRPC(
        weaviate_version=version,
        name="Dummy",
        tenant=None,
        consistency_level=None,
        validate_arguments=True,
        uses_125_api=True,
        uses_127_api=True,
    )


def _aggregate(version: _ServerVersion) -> _AggregateGRPC:
    return _AggregateGRPC(
        weaviate_version=version,
        name="Dummy",
        tenant=None,
        consistency_level=None,
        validate_arguments=True,
    )


def _aggregate_hybrid(version: _ServerVersion, alpha: float) -> base_search_pb2.Hybrid:
    return (
        _aggregate(version)
        .hybrid(
            query="cats",
            alpha=alpha,
            vector=None,
            properties=None,
            target_vector=None,
            bm25_operator=None,
            aggregations=[],
            filters=None,
            group_by=None,
            limit=None,
            object_limit=None,
            objects_count=True,
        )
        .hybrid
    )


@pytest.mark.parametrize("version", _BEFORE_1_36_7)
def test_hybrid_before_1_36_7_uses_legacy_alpha(version: _ServerVersion) -> None:
    default = _query(version).hybrid(query="cats", limit=5).hybrid_search
    assert default.use_alpha_param is False
    assert not default.HasField("alpha_param")
    assert default.alpha == pytest.approx(0.7)

    explicit = _query(version).hybrid(query="cats", alpha=0.25, limit=5).hybrid_search
    assert explicit.use_alpha_param is False
    assert explicit.alpha == pytest.approx(0.25)


@pytest.mark.parametrize("version", _BEFORE_1_36_7)
def test_aggregate_hybrid_before_1_36_7_uses_legacy_alpha(version: _ServerVersion) -> None:
    hybrid = _aggregate_hybrid(version, alpha=0.25)
    assert hybrid.use_alpha_param is False
    assert hybrid.alpha == pytest.approx(0.25)


@pytest.mark.parametrize("version", _FROM_1_36_7)
def test_hybrid_from_1_36_7_uses_alpha_param(version: _ServerVersion) -> None:
    default = _query(version).hybrid(query="cats", limit=5).hybrid_search
    assert default.use_alpha_param is True
    assert not default.HasField("alpha_param")

    explicit = _query(version).hybrid(query="cats", alpha=0.25, limit=5).hybrid_search
    assert explicit.use_alpha_param is True
    assert explicit.alpha_param == pytest.approx(0.25)


@pytest.mark.parametrize("version", _FROM_1_36_7)
def test_aggregate_hybrid_from_1_36_7_uses_alpha_param(version: _ServerVersion) -> None:
    hybrid = _aggregate_hybrid(version, alpha=0.25)
    assert hybrid.use_alpha_param is True
    assert hybrid.alpha_param == pytest.approx(0.25)
