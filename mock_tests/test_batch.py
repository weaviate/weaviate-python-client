from typing import Generator

import grpc
import pytest
import weaviate
from weaviate.proto.v1 import batch_pb2, weaviate_pb2_grpc
from .conftest import MOCK_IP, MOCK_PORT, MOCK_PORT_GRPC, mock_class, HTTPServer

HOW_MANY = 1000


class MockCanceledStreamWeaviateService(weaviate_pb2_grpc.WeaviateServicer):
    called = False
    uuids = set[str]()

    def BatchStream(
        self,
        request_iterator: Generator[batch_pb2.BatchStreamRequest, None, None],
        context: grpc.ServicerContext,
    ) -> Generator[batch_pb2.BatchStreamReply, None, None]:
        if not self.called:
            self.called = True
            context.set_code(grpc.StatusCode.CANCELLED)
            context.set_details("context canceled")
            return
        yield batch_pb2.BatchStreamReply(started=batch_pb2.BatchStreamReply.Started())
        for request in request_iterator:
            if request.HasField("data"):
                uuids = [obj.uuid for obj in request.data.objects.values]
                self.uuids.update(uuids)
                yield batch_pb2.BatchStreamReply(acks=batch_pb2.BatchStreamReply.Acks(uuids=uuids))
            if request.HasField("stop"):
                return


@pytest.fixture(scope="function")
def canceled_stream_client(
    weaviate_mock: HTTPServer, start_grpc_server: grpc.Server
) -> Generator[weaviate.WeaviateClient, None, None]:
    weaviate_mock.expect_request(f"/v1/schema/{mock_class['class']}").respond_with_json(mock_class)
    client = weaviate.connect_to_local(port=MOCK_PORT, host=MOCK_IP, grpc_port=MOCK_PORT_GRPC)
    yield client
    client.close()


@pytest.fixture(scope="function")
def canceled_stream(
    canceled_stream_client: weaviate.WeaviateClient, start_grpc_server: grpc.Server
):
    service = MockCanceledStreamWeaviateService()
    weaviate_pb2_grpc.add_WeaviateServicer_to_server(service, start_grpc_server)
    return canceled_stream_client.collections.use(mock_class["class"]), service


def test_ssb_canceled_stream(
    canceled_stream: tuple[weaviate.collections.Collection, MockCanceledStreamWeaviateService],
):
    collection, service = canceled_stream
    with collection.batch.stream() as batch:
        for i in range(HOW_MANY):
            batch.add_object({"name": f"Object {i}"})
    assert len(service.uuids) == HOW_MANY
