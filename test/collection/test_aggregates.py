import pytest
from typing import Awaitable
from weaviate.connect import ConnectionV4
from weaviate.collections.aggregate import _AggregateCollectionAsync
from weaviate.exceptions import WeaviateInvalidInputError


async def _test_aggregate(aggregate: Awaitable) -> None:
    with pytest.raises(WeaviateInvalidInputError):
        await aggregate()


@pytest.mark.asyncio
async def test_bad_aggregate_inputs(connection: ConnectionV4) -> None:
    aggregate = _AggregateCollectionAsync(connection, "dummy", None, None)
    # over_all
    await _test_aggregate(lambda: aggregate.over_all(filters="wrong"))
    await _test_aggregate(lambda: aggregate.over_all(group_by=42))
    await _test_aggregate(lambda: aggregate.over_all(total_count="wrong"))
    await _test_aggregate(lambda: aggregate.over_all(return_metrics="wrong"))

    # near text
    await _test_aggregate(lambda: aggregate.near_text(42))
    await _test_aggregate(lambda: aggregate.near_text("hi", certainty="wrong"))
    await _test_aggregate(lambda: aggregate.near_text("hi", distance="wrong"))
    await _test_aggregate(lambda: aggregate.near_text("hi", move_to="wrong"))
    await _test_aggregate(lambda: aggregate.near_text("hi", move_away="wrong"))
    await _test_aggregate(lambda: aggregate.near_text("hi", object_limit="wrong"))

    # near object
    await _test_aggregate(lambda: aggregate.near_object(42))

    # near vector
    await _test_aggregate(lambda: aggregate.near_vector(42))

    # near image
    await _test_aggregate(lambda: aggregate.near_image(42))
