from typing import Callable

import pytest

from weaviate.classes.query import HybridVector, NearVector, TargetVectors
from weaviate.collections.classes.grpc import NearVectorInputType, TargetVectorJoinType
from weaviate.collections.grpc.query import _QueryGRPC
from weaviate.exceptions import WeaviateInvalidInputError
from weaviate.proto.v1 import base_search_pb2
from weaviate.util import _ServerVersion


def _query() -> _QueryGRPC:
    return _QueryGRPC(
        weaviate_version=_ServerVersion.from_string("1.36.9"),
        name="Documents",
        tenant=None,
        consistency_level=None,
        validate_arguments=True,
    )


def _near_vector(
    vector: NearVectorInputType, target_vector: TargetVectorJoinType
) -> base_search_pb2.Targets:
    request = _query().near_vector(near_vector=vector, target_vector=target_vector)
    return request.near_vector.targets


def _hybrid(
    vector: NearVectorInputType, target_vector: TargetVectorJoinType
) -> base_search_pb2.Targets:
    request = _query().hybrid(query="example", vector=vector, target_vector=target_vector)
    return request.hybrid_search.targets


def _hybrid_near_vector(
    vector: NearVectorInputType, target_vector: TargetVectorJoinType
) -> base_search_pb2.Targets:
    request = _query().hybrid(
        query="example", vector=HybridVector.near_vector(vector), target_vector=target_vector
    )
    return request.hybrid_search.targets


Search = Callable[[NearVectorInputType, TargetVectorJoinType], base_search_pb2.Targets]
SEARCHES = [_near_vector, _hybrid, _hybrid_near_vector]


@pytest.mark.parametrize("search", SEARCHES)
@pytest.mark.parametrize(
    "target_vector",
    [["title", "summary"], TargetVectors.manual_weights({"title": 1.0, "summary": 2.0})],
    ids=["list", "weights"],
)
def test_mismatched_vector_names(search: Search, target_vector: TargetVectorJoinType) -> None:
    with pytest.raises(WeaviateInvalidInputError, match="must match the target vectors"):
        search({"title": [1.0, 0.0], "body": [0.0, 1.0]}, target_vector)


@pytest.mark.parametrize("search", SEARCHES)
def test_vector_names_in_a_different_order(search: Search) -> None:
    targets = search(
        {"summary": [0.0, 1.0], "title": [1.0, 0.0]},
        TargetVectors.manual_weights({"title": 1.0, "summary": 2.0}),
    )
    weights = {weight.target: weight.weight for weight in targets.weights_for_targets}
    assert weights == {"title": 1.0, "summary": 2.0}
    assert list(targets.target_vectors) == ["summary", "title"]


@pytest.mark.parametrize("search", SEARCHES)
def test_repeated_target_vector_names_with_multiple_weights(search: Search) -> None:
    targets = search(
        {"title": NearVector.list_of_vectors([1.0, 0.0], [0.0, 1.0])},
        TargetVectors.manual_weights({"title": [1.0, 2.0]}),
    )
    assert list(targets.target_vectors) == ["title", "title"]
    assert [(weight.target, weight.weight) for weight in targets.weights_for_targets] == [
        ("title", 1.0),
        ("title", 2.0),
    ]
