import pytest

from weaviate.classes.query import HybridVector, NearVector, TargetVectors
from weaviate.collections.classes.grpc import NearVectorInputType, TargetVectorJoinType
from weaviate.collections.grpc.query import _QueryGRPC
from weaviate.exceptions import WeaviateInvalidInputError
from weaviate.proto.v1 import search_get_pb2
from weaviate.util import _ServerVersion


def _request(
    version: str,
    query_type: str,
    vector: NearVectorInputType,
    target_vector: TargetVectorJoinType,
) -> search_get_pb2.SearchRequest:
    query = _QueryGRPC(
        weaviate_version=_ServerVersion.from_string(version),
        name="Documents",
        tenant=None,
        consistency_level=None,
        validate_arguments=True,
        uses_125_api=True,
        uses_127_api=True,
    )
    if query_type == "near_vector":
        return query.near_vector(near_vector=vector, target_vector=target_vector)
    return query.hybrid(
        query="example",
        vector=HybridVector.near_vector(vector) if query_type == "hybrid_near_vector" else vector,
        target_vector=target_vector,
    )


@pytest.mark.parametrize("version", ["1.26.0", "1.27.0", "1.29.0"])
@pytest.mark.parametrize("query_type", ["near_vector", "hybrid", "hybrid_near_vector"])
@pytest.mark.parametrize("weighted", [False, True])
def test_mismatched_target_vector_names(version: str, query_type: str, weighted: bool) -> None:
    target_vector = (
        TargetVectors.manual_weights({"title": 1.0, "summary": 2.0})
        if weighted
        else ["title", "summary"]
    )
    with pytest.raises(WeaviateInvalidInputError):
        _request(version, query_type, {"title": [1.0, 0.0], "body": [0.0, 1.0]}, target_vector)


@pytest.mark.parametrize("version", ["1.26.0", "1.27.0", "1.29.0"])
@pytest.mark.parametrize("query_type", ["near_vector", "hybrid", "hybrid_near_vector"])
def test_target_vector_names_can_be_in_a_different_order(version: str, query_type: str) -> None:
    request = _request(
        version,
        query_type,
        {"summary": [0.0, 1.0], "title": [1.0, 0.0]},
        TargetVectors.manual_weights({"title": 1.0, "summary": 2.0}),
    )
    targets = (
        request.near_vector.targets
        if query_type == "near_vector"
        else request.hybrid_search.targets
    )
    assert set(targets.target_vectors) == {"title", "summary"}
    assert {weight.target: weight.weight for weight in targets.weights_for_targets} == {
        "title": 1.0,
        "summary": 2.0,
    }


@pytest.mark.parametrize("version", ["1.27.0", "1.29.0"])
@pytest.mark.parametrize("query_type", ["near_vector", "hybrid", "hybrid_near_vector"])
def test_repeated_target_vector_names_with_multiple_weights(version: str, query_type: str) -> None:
    request = _request(
        version,
        query_type,
        {"title": NearVector.list_of_vectors([1.0, 0.0], [0.0, 1.0])},
        TargetVectors.manual_weights({"title": [1.0, 2.0]}),
    )
    targets = (
        request.near_vector.targets
        if query_type == "near_vector"
        else request.hybrid_search.targets
    )
    assert list(targets.target_vectors) == ["title", "title"]
    assert [(weight.target, weight.weight) for weight in targets.weights_for_targets] == [
        ("title", 1.0),
        ("title", 2.0),
    ]
