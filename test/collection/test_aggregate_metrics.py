from typing import Optional
from unittest.mock import patch

import pytest

from weaviate import WeaviateClient
from weaviate.classes.aggregate import Metrics
from weaviate.connect import ConnectionParams
from weaviate.proto.v1 import aggregate_pb2
from weaviate.util import _ServerVersion


@pytest.mark.parametrize("limit", [None, 3])
@pytest.mark.parametrize(
    "count,top_occurrences_count,top_occurrences_value,expected_top_occurrences",
    [
        (False, False, False, True),  # All-false arguments select all text metrics.
        (False, False, True, True),
        (False, True, False, True),
        (False, True, True, True),
        (True, False, False, False),
        (True, False, True, True),
        (True, True, False, True),
        (True, True, True, True),
    ],
)
def test_text_top_occurrences_grpc_request(
    count: bool,
    top_occurrences_count: bool,
    top_occurrences_value: bool,
    expected_top_occurrences: bool,
    limit: Optional[int],
) -> None:
    client = WeaviateClient(
        connection_params=ConnectionParams.from_url("http://localhost:8080", 50051),
        skip_init_checks=True,
    )
    client._connection._weaviate_version = _ServerVersion.from_string("1.29.0")
    metric = Metrics("title").text(
        count=count,
        top_occurrences_count=top_occurrences_count,
        top_occurrences_value=top_occurrences_value,
        limit=limit,
    )
    try:
        with patch.object(
            client._connection,
            "grpc_aggregate",
            return_value=aggregate_pb2.AggregateReply(),
        ) as send:
            client.collections.use("Article").aggregate.over_all(return_metrics=metric)

        request = aggregate_pb2.AggregateRequest.FromString(
            send.call_args.kwargs["request"].SerializeToString()
        )
        assert request.collection == "Article"
        assert len(request.aggregations) == 1
        aggregation = request.aggregations[0]
        assert aggregation.property == "title"
        assert aggregation.text.count == metric.count
        assert aggregation.text.top_occurences == expected_top_occurrences
        assert aggregation.text.HasField("top_occurences_limit") == (limit is not None)
        if limit is not None:
            assert aggregation.text.top_occurences_limit == limit
    finally:
        client.close()
