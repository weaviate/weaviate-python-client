from unittest.mock import patch

import pytest

from weaviate.collections.classes.grpc import GroupBy, Rerank
from weaviate.collections.collection.async_ import CollectionAsync
from weaviate.connect import ConnectionV4
from weaviate.proto.v1 import search_get_pb2
from weaviate.util import _ServerVersion


@pytest.fixture
def collection(connection: ConnectionV4) -> CollectionAsync:
    connection._weaviate_version = _ServerVersion(1, 39, 0)
    return CollectionAsync(connection, "Test", True)


@pytest.fixture
def group() -> search_get_pb2.GroupByResult:
    return search_get_pb2.GroupByResult(
        name="books",
        number_of_objects=1,
        min_distance=0.25,
        max_distance=0.25,
        objects=[
            {
                "properties": {
                    "target_collection": "Test",
                    "non_ref_props": {"fields": {"category": {"text_value": "books"}}},
                },
                "metadata": {"id_as_bytes": bytes.fromhex("12345678123456781234567812345678")},
            }
        ],
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("method", ["near_text", "near_vector"])
@pytest.mark.parametrize("score", [None, 0.0, 0.75])
async def test_grouped_query_preserves_optional_rerank_score(
    connection: ConnectionV4,
    collection: CollectionAsync,
    group: search_get_pb2.GroupByResult,
    method: str,
    score: float | None,
) -> None:
    if score is not None:
        group.rerank.score = score
    response = search_get_pb2.SearchReply(group_by_results=[group])
    with patch.object(connection, "grpc_search", return_value=response) as search:
        result = await getattr(collection.query, method)(
            ["books"] if method == "near_text" else [1.0, 0.0],
            group_by=GroupBy(prop="category", number_of_groups=1, objects_per_group=1),
            rerank=Rerank(prop="category") if score is not None else None,
        )

    search.assert_called_once()
    assert result.groups["books"].rerank_score == score
    assert result.groups["books"].objects[0].properties == {"category": "books"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "score,generated",
    [(None, None), (0.0, ""), (0.75, "summary"), (0.75, None), (None, "summary")],
)
async def test_grouped_generate_preserves_optional_results(
    connection: ConnectionV4,
    collection: CollectionAsync,
    group: search_get_pb2.GroupByResult,
    score: float | None,
    generated: str | None,
) -> None:
    if score is not None:
        group.rerank.score = score
    if generated is not None:
        group.generative.result = generated
    response = search_get_pb2.SearchReply(group_by_results=[group])
    with patch.object(connection, "grpc_search", return_value=response) as search:
        result = await collection.generate.near_vector(
            [1.0, 0.0],
            single_prompt="Describe {category}",
            grouped_task="Summarize these categories" if generated is not None else None,
            group_by=GroupBy(prop="category", number_of_groups=1, objects_per_group=1),
            rerank=Rerank(prop="category") if score is not None else None,
        )

    search.assert_called_once()
    assert result.groups["books"].rerank_score == score
    assert result.groups["books"].generated == generated
    assert result.groups["books"].objects[0].properties == {"category": "books"}
