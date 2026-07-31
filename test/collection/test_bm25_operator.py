"""Unit tests: BM25 search operators are wired into the gRPC request and version-gated.

``BM25Operator.and_cross()`` maps to the ``OPERATOR_AND_CROSS`` enum added in Weaviate 1.39.0 and
backported to 1.38.8 and 1.37.15, so the client must reject it on servers outside those ranges
rather than send an enum value the server will not understand.
"""

from typing import Optional

import pytest

from weaviate.classes.query import BM25Operator
from weaviate.collections.classes.grpc import BM25OperatorOptions
from weaviate.collections.grpc.aggregate import _AggregateGRPC
from weaviate.collections.grpc.query import _QueryGRPC
from weaviate.exceptions import WeaviateUnsupportedFeatureError
from weaviate.proto.v1 import base_search_pb2
from weaviate.util import _ServerVersion

_SUPPORTED = ["1.37.15", "1.38.8", "1.39.0", "1.40.0"]
_UNSUPPORTED = ["1.36.9", "1.37.14", "1.38.0", "1.38.7"]


def _query(version: str = "1.39.0") -> _QueryGRPC:
    return _QueryGRPC(
        weaviate_version=_ServerVersion.from_string(version),
        name="Dummy",
        tenant=None,
        consistency_level=None,
        validate_arguments=True,
        uses_125_api=True,
        uses_127_api=True,
    )


def _aggregate(version: str = "1.39.0") -> _AggregateGRPC:
    return _AggregateGRPC(
        weaviate_version=_ServerVersion.from_string(version),
        name="Dummy",
        tenant=None,
        consistency_level=None,
        validate_arguments=True,
    )


def _aggregate_hybrid(
    builder: _AggregateGRPC, operator: Optional[BM25OperatorOptions]
) -> base_search_pb2.Hybrid:
    return builder.hybrid(
        query="banana two",
        alpha=0.0,
        vector=None,
        properties=None,
        target_vector=None,
        bm25_operator=operator,
        aggregations=[],
        filters=None,
        group_by=None,
        limit=None,
        object_limit=None,
        objects_count=False,
    ).hybrid


@pytest.mark.parametrize(
    "operator,expected,minimum_or_tokens_match",
    [
        (BM25Operator.and_(), base_search_pb2.SearchOperatorOptions.OPERATOR_AND, 0),
        (BM25Operator.or_(minimum_match=2), base_search_pb2.SearchOperatorOptions.OPERATOR_OR, 2),
        (
            BM25Operator.and_cross(),
            base_search_pb2.SearchOperatorOptions.OPERATOR_AND_CROSS,
            0,
        ),
    ],
)
def test_bm25_operator_wired_into_request(
    operator: BM25OperatorOptions,
    expected: "base_search_pb2.SearchOperatorOptions.Operator",
    minimum_or_tokens_match: int,
) -> None:
    search_operator = (
        _query().bm25(query="banana two", operator=operator).bm25_search.search_operator
    )
    assert search_operator.operator == expected
    assert search_operator.minimum_or_tokens_match == minimum_or_tokens_match


@pytest.mark.parametrize(
    "operator,expected",
    [
        (BM25Operator.and_(), base_search_pb2.SearchOperatorOptions.OPERATOR_AND),
        (BM25Operator.or_(minimum_match=2), base_search_pb2.SearchOperatorOptions.OPERATOR_OR),
        (BM25Operator.and_cross(), base_search_pb2.SearchOperatorOptions.OPERATOR_AND_CROSS),
    ],
)
def test_hybrid_bm25_operator_wired_into_request(
    operator: BM25OperatorOptions, expected: "base_search_pb2.SearchOperatorOptions.Operator"
) -> None:
    req = _query().hybrid(query="banana two", alpha=0.0, bm25_operator=operator)
    assert req.hybrid_search.bm25_search_operator.operator == expected


def test_no_operator_leaves_search_operator_unset() -> None:
    assert not _query().bm25(query="banana two").bm25_search.HasField("search_operator")
    req = _query().hybrid(query="banana two", alpha=0.0)
    assert not req.hybrid_search.HasField("bm25_search_operator")


@pytest.mark.parametrize("version", _SUPPORTED)
def test_and_cross_allowed_on_supported_versions(version: str) -> None:
    req = _query(version).bm25(query="banana two", operator=BM25Operator.and_cross())
    assert (
        req.bm25_search.search_operator.operator
        == base_search_pb2.SearchOperatorOptions.OPERATOR_AND_CROSS
    )


@pytest.mark.parametrize("version", _UNSUPPORTED)
def test_and_cross_rejected_on_unsupported_versions(version: str) -> None:
    with pytest.raises(WeaviateUnsupportedFeatureError) as e:
        _query(version).bm25(query="banana two", operator=BM25Operator.and_cross())
    assert "1.37.15 or 1.38.8 or 1.39.0" in str(e.value)
    assert version in str(e.value)


@pytest.mark.parametrize("version", _UNSUPPORTED)
def test_hybrid_and_cross_rejected_on_unsupported_versions(version: str) -> None:
    with pytest.raises(WeaviateUnsupportedFeatureError):
        _query(version).hybrid(
            query="banana two", alpha=0.0, bm25_operator=BM25Operator.and_cross()
        )


@pytest.mark.parametrize("version", _UNSUPPORTED)
def test_aggregate_hybrid_and_cross_rejected_on_unsupported_versions(version: str) -> None:
    with pytest.raises(WeaviateUnsupportedFeatureError):
        _aggregate_hybrid(_aggregate(version), BM25Operator.and_cross())


def test_aggregate_hybrid_and_cross_allowed_on_supported_version() -> None:
    hybrid = _aggregate_hybrid(_aggregate("1.39.0"), BM25Operator.and_cross())
    assert (
        hybrid.bm25_search_operator.operator
        == base_search_pb2.SearchOperatorOptions.OPERATOR_AND_CROSS
    )


@pytest.mark.parametrize("version", _UNSUPPORTED)
@pytest.mark.parametrize("operator", [BM25Operator.and_(), BM25Operator.or_(minimum_match=1), None])
def test_other_operators_unaffected_by_gate(
    version: str, operator: Optional[BM25OperatorOptions]
) -> None:
    _query(version).bm25(query="banana two", operator=operator)
    _query(version).hybrid(query="banana two", alpha=0.0, bm25_operator=operator)
