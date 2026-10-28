from typing import List

import grpc
import pytest

import weaviate
from weaviate.classes.query import Metrics
from weaviate.proto.v1 import aggregate_pb2, weaviate_pb2_grpc


class MockAggregateService(weaviate_pb2_grpc.WeaviateServicer):
    def __init__(self) -> None:
        self.requests: List[aggregate_pb2.AggregateRequest] = []

    def Aggregate(
        self, request: aggregate_pb2.AggregateRequest, context: grpc.ServicerContext
    ) -> aggregate_pb2.AggregateReply:
        self.requests.append(request)
        return aggregate_pb2.AggregateReply(
            single_result=aggregate_pb2.AggregateReply.Single(objects_count=3)
        )


@pytest.fixture(scope="function")
def aggregate_service(start_grpc_server: grpc.Server) -> MockAggregateService:
    service = MockAggregateService()
    weaviate_pb2_grpc.add_WeaviateServicer_to_server(service, start_grpc_server)
    return service


def test_aggregate_near_image_sends_the_image(
    weaviate_client: weaviate.WeaviateClient, aggregate_service: MockAggregateService
) -> None:
    collection = weaviate_client.collections.use("NearImageAggregate")

    res = collection.aggregate.near_image(
        "aGVsbG8=",
        certainty=0.7,
        total_count=True,
        return_metrics=Metrics("rating").integer(count=True),
    )

    assert res.total_count == 3
    assert len(aggregate_service.requests) == 1
    request = aggregate_service.requests[0]
    assert request.WhichOneof("search") == "near_image"
    assert request.near_image.image == "aGVsbG8="
    assert request.near_image.certainty == pytest.approx(0.7)
