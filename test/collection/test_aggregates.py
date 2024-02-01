import pytest
from typing import Callable
from weaviate.connect import ConnectionV4
from weaviate.collections.aggregate import _AggregateCollection
from weaviate.exceptions import WeaviateInvalidInputError


def _test_aggregate(aggregate: Callable) -> None:
    with pytest.raises(WeaviateInvalidInputError):
        aggregate()


def test_bad_aggregate_inputs(connection: ConnectionV4) -> None:
    aggregate = _AggregateCollection(connection, "dummy", None, None)
    # over_all
    _test_aggregate(lambda: aggregate.over_all(filters="wrong"))
    _test_aggregate(lambda: aggregate.over_all(group_by=42))
    _test_aggregate(lambda: aggregate.over_all(total_count="wrong"))
    _test_aggregate(lambda: aggregate.over_all(return_metrics="wrong"))

    # near text
    _test_aggregate(lambda: aggregate.near_text(42))
    _test_aggregate(lambda: aggregate.near_text("hi", certainty="wrong"))
    _test_aggregate(lambda: aggregate.near_text("hi", distance="wrong"))
    _test_aggregate(lambda: aggregate.near_text("hi", move_to="wrong"))
    _test_aggregate(lambda: aggregate.near_text("hi", move_away="wrong"))
    _test_aggregate(lambda: aggregate.near_text("hi", object_limit="wrong"))

    # near object
    _test_aggregate(lambda: aggregate.near_object(42))

    # near vector
    _test_aggregate(lambda: aggregate.near_vector(42))

    # near image
    _test_aggregate(lambda: aggregate.near_image(42))
