import pytest

from weaviate.classes.query import BM25Operator
from weaviate.collections.grpc.query import _QueryGRPC
from weaviate.exceptions import WeaviateUnsupportedFeatureError
from weaviate.proto.v1 import base_search_pb2
from weaviate.util import _ServerVersion

_AND_CROSS = base_search_pb2.SearchOperatorOptions.OPERATOR_AND_CROSS


def _builder(version: str = "1.39.0") -> _QueryGRPC:
    return _QueryGRPC(
        weaviate_version=_ServerVersion.from_string(version),
        name="Dummy",
        tenant=None,
        consistency_level=None,
        validate_arguments=True,
        uses_125_api=True,
        uses_127_api=True,
    )


def test_and_cross_wired_into_request() -> None:
    bm25 = _builder().bm25(query="banana split", operator=BM25Operator.and_cross())
    assert bm25.bm25_search.search_operator.operator == _AND_CROSS

    hybrid = _builder().hybrid(
        query="banana split", alpha=0.0, bm25_operator=BM25Operator.and_cross()
    )
    assert hybrid.hybrid_search.bm25_search_operator.operator == _AND_CROSS


@pytest.mark.parametrize("version", ["1.37.14", "1.38.7"])
def test_and_cross_rejected_on_unsupported_versions(version: str) -> None:
    with pytest.raises(WeaviateUnsupportedFeatureError):
        _builder(version).bm25(query="banana split", operator=BM25Operator.and_cross())
