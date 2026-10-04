import threading
import time
import uuid
from typing import AsyncGenerator, Generator, List, Set

import grpc
import pytest
import pytest_asyncio
import weaviate
from weaviate.classes.init import AdditionalConfig, Timeout
from weaviate.proto.v1 import batch_pb2, weaviate_pb2_grpc
from .conftest import MOCK_IP, MOCK_PORT, MOCK_PORT_GRPC, mock_class, HTTPServer

FAILING_UUID = str(uuid.UUID(int=1))
SUCCEEDING_UUID = str(uuid.UUID(int=2))

# A stuck stream is only abandoned after the shutdown timeout (insert + 5s), so a short insert
# timeout keeps a regression from blocking the suite while still failing the exit-time check.
INSERT_TIMEOUT = 1
MAX_EXIT_SECONDS = 5


class MockRejectingWeaviateService(weaviate_pb2_grpc.WeaviateServicer):
    """Rejects the object FAILING_UUID and every reference that touches it."""

    def __init__(self) -> None:
        self.references: List[batch_pb2.BatchReference] = []

    def BatchStream(
        self,
        request_iterator: Generator[batch_pb2.BatchStreamRequest, None, None],
        context: grpc.ServicerContext,
    ) -> Generator[batch_pb2.BatchStreamReply, None, None]:
        yield batch_pb2.BatchStreamReply(started=batch_pb2.BatchStreamReply.Started())
        for request in request_iterator:
            if request.HasField("data"):
                uuids: List[str] = []
                beacons: List[str] = []
                errors: List[batch_pb2.BatchStreamReply.Results.Error] = []
                successes: List[batch_pb2.BatchStreamReply.Results.Success] = []
                for obj in request.data.objects.values:
                    uuids.append(obj.uuid)
                    if obj.uuid == FAILING_UUID:
                        errors.append(
                            batch_pb2.BatchStreamReply.Results.Error(
                                uuid=obj.uuid, error="mock object failure"
                            )
                        )
                    else:
                        successes.append(batch_pb2.BatchStreamReply.Results.Success(uuid=obj.uuid))
                for ref in request.data.references.values:
                    self.references.append(ref)
                    beacon = (
                        f"weaviate://localhost/{ref.from_collection}/{ref.from_uuid}/{ref.name}"
                    )
                    beacons.append(beacon)
                    if FAILING_UUID in (ref.from_uuid, ref.to_uuid):
                        errors.append(
                            batch_pb2.BatchStreamReply.Results.Error(
                                beacon=beacon, error="mock reference failure"
                            )
                        )
                    else:
                        successes.append(batch_pb2.BatchStreamReply.Results.Success(beacon=beacon))
                yield batch_pb2.BatchStreamReply(
                    acks=batch_pb2.BatchStreamReply.Acks(uuids=uuids, beacons=beacons)
                )
                yield batch_pb2.BatchStreamReply(
                    results=batch_pb2.BatchStreamReply.Results(errors=errors, successes=successes)
                )
            if request.HasField("stop"):
                return


def _alive_batch_loop_threads() -> Set[threading.Thread]:
    return {t for t in threading.enumerate() if t.name == "BgBatchLoop" and t.is_alive()}


@pytest.fixture(scope="function")
def rejecting_service(start_grpc_server: grpc.Server) -> MockRejectingWeaviateService:
    service = MockRejectingWeaviateService()
    weaviate_pb2_grpc.add_WeaviateServicer_to_server(service, start_grpc_server)
    return service


@pytest.fixture(scope="function")
def short_insert_timeout_client(
    weaviate_mock: HTTPServer, start_grpc_server: grpc.Server
) -> Generator[weaviate.WeaviateClient, None, None]:
    weaviate_mock.expect_request(f"/v1/schema/{mock_class['class']}").respond_with_json(mock_class)
    client = weaviate.connect_to_local(
        port=MOCK_PORT,
        host=MOCK_IP,
        grpc_port=MOCK_PORT_GRPC,
        additional_config=AdditionalConfig(timeout=Timeout(insert=INSERT_TIMEOUT)),
    )
    yield client
    client.close()


@pytest_asyncio.fixture
async def short_insert_timeout_client_async(
    weaviate_mock: HTTPServer, start_grpc_server: grpc.Server
) -> AsyncGenerator[weaviate.WeaviateAsyncClient, None]:
    weaviate_mock.expect_request(f"/v1/schema/{mock_class['class']}").respond_with_json(mock_class)
    client = weaviate.use_async_with_local(
        port=MOCK_PORT,
        host=MOCK_IP,
        grpc_port=MOCK_PORT_GRPC,
        additional_config=AdditionalConfig(timeout=Timeout(insert=INSERT_TIMEOUT)),
    )
    await client.connect()
    yield client
    await client.close()


@pytest.mark.timeout(60)
def test_ssb_stream_sends_reference_to_failed_object(
    short_insert_timeout_client: weaviate.WeaviateClient,
    rejecting_service: MockRejectingWeaviateService,
) -> None:
    collection = short_insert_timeout_client.collections.use(mock_class["class"])
    loops_before = _alive_batch_loop_threads()

    start = time.time()
    with collection.batch.stream() as batch:
        batch.add_object({"name": "fails"}, uuid=FAILING_UUID)
        batch.add_object({"name": "succeeds"}, uuid=SUCCEEDING_UUID)
        batch.add_reference(from_uuid=SUCCEEDING_UUID, from_property="ref", to=FAILING_UUID)
    elapsed = time.time() - start

    assert elapsed < MAX_EXIT_SECONDS
    assert _alive_batch_loop_threads() - loops_before == set()
    failed_refs = collection.batch.failed_references
    assert [ref.to_uuid for ref in rejecting_service.references] == [FAILING_UUID]
    assert [str(err.object_.uuid) for err in collection.batch.failed_objects] == [FAILING_UUID]
    assert [str(err.reference.to_object_uuid) for err in failed_refs] == [FAILING_UUID]


@pytest.mark.timeout(60)
@pytest.mark.asyncio
async def test_ssb_stream_sends_reference_to_failed_object_async(
    short_insert_timeout_client_async: weaviate.WeaviateAsyncClient,
    rejecting_service: MockRejectingWeaviateService,
) -> None:
    collection = short_insert_timeout_client_async.collections.use(mock_class["class"])

    start = time.time()
    async with collection.batch.stream() as batch:
        await batch.add_object({"name": "fails"}, uuid=FAILING_UUID)
        await batch.add_object({"name": "succeeds"}, uuid=SUCCEEDING_UUID)
        await batch.add_reference(from_uuid=SUCCEEDING_UUID, from_property="ref", to=FAILING_UUID)
    elapsed = time.time() - start

    assert elapsed < MAX_EXIT_SECONDS
    failed_refs = collection.batch.failed_references
    assert [ref.to_uuid for ref in rejecting_service.references] == [FAILING_UUID]
    assert [str(err.object_.uuid) for err in collection.batch.failed_objects] == [FAILING_UUID]
    assert [str(err.reference.to_object_uuid) for err in failed_refs] == [FAILING_UUID]
