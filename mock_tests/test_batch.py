from typing import AsyncGenerator, Generator, List

import grpc
import pytest
import pytest_asyncio
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


class MockFailedObjectWeaviateService(weaviate_pb2_grpc.WeaviateServicer):
    """Rejects every other object, starting with the first.

    A batch of 1 object gives 1 error and 0 uuids; a batch of 4 gives 2 errors and 2 uuids.
    """

    def __init__(self) -> None:
        self.seen = 0

    def BatchStream(
        self,
        request_iterator: Generator[batch_pb2.BatchStreamRequest, None, None],
        context: grpc.ServicerContext,
    ) -> Generator[batch_pb2.BatchStreamReply, None, None]:
        yield batch_pb2.BatchStreamReply(started=batch_pb2.BatchStreamReply.Started())
        for request in request_iterator:
            if request.HasField("data"):
                uuids: List[str] = []
                errors: List[batch_pb2.BatchStreamReply.Results.Error] = []
                successes: List[batch_pb2.BatchStreamReply.Results.Success] = []
                for obj in request.data.objects.values:
                    uuids.append(obj.uuid)
                    if self.seen % 2 == 0:
                        errors.append(
                            batch_pb2.BatchStreamReply.Results.Error(
                                uuid=obj.uuid, error="mock failure"
                            )
                        )
                    else:
                        successes.append(batch_pb2.BatchStreamReply.Results.Success(uuid=obj.uuid))
                    self.seen += 1
                yield batch_pb2.BatchStreamReply(acks=batch_pb2.BatchStreamReply.Acks(uuids=uuids))
                yield batch_pb2.BatchStreamReply(
                    results=batch_pb2.BatchStreamReply.Results(errors=errors, successes=successes)
                )
            if request.HasField("stop"):
                return


@pytest.fixture(scope="function")
def failed_object_stream(
    canceled_stream_client: weaviate.WeaviateClient, start_grpc_server: grpc.Server
):
    service = MockFailedObjectWeaviateService()
    weaviate_pb2_grpc.add_WeaviateServicer_to_server(service, start_grpc_server)
    return canceled_stream_client.collections.use(mock_class["class"])


@pytest_asyncio.fixture
async def failed_object_stream_async(
    weaviate_mock: HTTPServer, start_grpc_server: grpc.Server
) -> AsyncGenerator[weaviate.collections.CollectionAsync, None]:
    weaviate_mock.expect_request(f"/v1/schema/{mock_class['class']}").respond_with_json(mock_class)
    weaviate_pb2_grpc.add_WeaviateServicer_to_server(
        MockFailedObjectWeaviateService(), start_grpc_server
    )
    client = weaviate.use_async_with_local(port=MOCK_PORT, host=MOCK_IP, grpc_port=MOCK_PORT_GRPC)
    await client.connect()
    yield client.collections.use(mock_class["class"])
    await client.close()


def test_ingest_has_errors_on_failed_object(
    failed_object_stream: weaviate.collections.Collection,
):
    result = failed_object_stream.data.ingest([{"name": "Object 1"}])
    assert result.has_errors is True
    assert len(result.errors) == 1


def test_ssb_ingest_reports_has_errors(
    failed_object_stream: weaviate.collections.Collection,
) -> None:
    result = failed_object_stream.data.ingest({"name": f"Object {i}"} for i in range(4))
    assert len(result.errors) == 2
    assert len(result.uuids) == 2
    assert result.has_errors


@pytest.mark.asyncio
async def test_ssb_ingest_reports_has_errors_async(
    failed_object_stream_async: weaviate.collections.CollectionAsync,
) -> None:
    result = await failed_object_stream_async.data.ingest({"name": f"Object {i}"} for i in range(4))
    assert len(result.errors) == 2
    assert len(result.uuids) == 2
    assert result.has_errors


def test_ssb_stream_reports_has_errors(
    failed_object_stream: weaviate.collections.Collection,
) -> None:
    with failed_object_stream.batch.stream() as batch:
        for i in range(4):
            batch.add_object({"name": f"Object {i}"})
    assert len(failed_object_stream.batch.failed_objects) == 2
    assert failed_object_stream.batch.results.objs.has_errors
