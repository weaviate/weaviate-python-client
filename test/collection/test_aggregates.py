from typing import Awaitable, Callable

import pytest

from weaviate.collections.aggregate import _AggregateCollectionAsync
from weaviate.connect import ConnectionV4
from weaviate.exceptions import WeaviateInvalidInputError


async def _test_aggregate(aggregate: Callable[[], Awaitable]) -> None:
    with pytest.raises(WeaviateInvalidInputError):
        await aggregate()


@pytest.mark.asyncio
async def test_bad_aggregate_inputs(connection: ConnectionV4) -> None:
    aggregate = _AggregateCollectionAsync(connection, "dummy", None, None, True)
    # near text
    await _test_aggregate(lambda: aggregate.near_text(42, object_limit=10))
    await _test_aggregate(lambda: aggregate.near_text("hi", certainty="wrong"))
    await _test_aggregate(lambda: aggregate.near_text("hi", distance="wrong"))
    await _test_aggregate(lambda: aggregate.near_text("hi", move_to="wrong", object_limit=10))
    await _test_aggregate(lambda: aggregate.near_text("hi", move_away="wrong", object_limit=10))

    # near object
    await _test_aggregate(lambda: aggregate.near_object(42, object_limit=10))

    # near vector
    await _test_aggregate(lambda: aggregate.near_vector(42, object_limit=10))

    # near image
    await _test_aggregate(lambda: aggregate.near_image(42))
