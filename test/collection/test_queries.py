from typing import Awaitable

import pytest

from weaviate.collections.query import _QueryCollectionAsync
from weaviate.connect import ConnectionV4
from weaviate.exceptions import WeaviateInvalidInputError


async def _test_query(query: Awaitable) -> None:
    with pytest.raises(WeaviateInvalidInputError):
        await query()


@pytest.mark.asyncio
async def test_bad_query_inputs(connection: ConnectionV4) -> None:
    query = _QueryCollectionAsync(connection, "dummy", None, None, None, None, True)
    # fetch_objects
    await _test_query(lambda: query.fetch_objects(limit="thing"))
    await _test_query(lambda: query.fetch_objects(offset="wrong"))
    await _test_query(lambda: query.fetch_objects(after=42))
    await _test_query(lambda: query.fetch_objects(filters="wrong"))
    await _test_query(lambda: query.fetch_objects(sort="wrong"))
    await _test_query(lambda: query.fetch_objects(include_vector=42))
    await _test_query(lambda: query.fetch_objects(return_metadata=42))
    await _test_query(lambda: query.fetch_objects(return_properties=42))
    await _test_query(lambda: query.fetch_objects(return_references="wrong"))

    # bm25
    await _test_query(lambda: query.bm25(42))
    await _test_query(lambda: query.bm25("hi", query_properties="wrong"))
    await _test_query(lambda: query.bm25("hi", auto_limit="wrong"))
    await _test_query(lambda: query.bm25("hi", rerank="wrong"))

    # hybrid
    await _test_query(lambda: query.hybrid(42))
    await _test_query(lambda: query.hybrid("hi", query_properties="wrong"))
    await _test_query(lambda: query.hybrid("hi", alpha="wrong"))
    await _test_query(lambda: query.hybrid("hi", vector="wrong"))
    await _test_query(lambda: query.hybrid("hi", fusion_type="wrong"))

    # near text
    await _test_query(lambda: query.near_text(42))
    await _test_query(lambda: query.near_text("hi", certainty="wrong"))
    await _test_query(lambda: query.near_text("hi", distance="wrong"))
    await _test_query(lambda: query.near_text("hi", move_to="wrong"))
    await _test_query(lambda: query.near_text("hi", move_away="wrong"))

    # near object
    await _test_query(lambda: query.near_object(42))

    # near vector
    await _test_query(lambda: query.near_vector(42))

    # near image
    await _test_query(lambda: query.near_image(42))
