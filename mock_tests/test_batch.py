import asyncio
import threading
from queue import Queue
from typing import AsyncGenerator, Generator, List

import grpc
import pytest
import pytest_asyncio
import weaviate
from weaviate.collections.batch.async_ import _BatchBaseAsync
from weaviate.collections.batch.base import _BatchStreamRequest
from weaviate.collections.batch.grpc_batch import _BatchGRPC
from weaviate.collections.batch.sync import _BatchBaseSync
from weaviate.proto.v1 import batch_pb2, weaviate_pb2_grpc
from weaviate.util import _ServerVersion
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


def _make_sync_batch() -> _BatchBaseSync:
    # build a _BatchBaseSync without a connection, setting only the fields
    # __send and __put_back read, so the stale-sender race can be driven
    # deterministically without a server
    batch = object.__new__(_BatchBaseSync)
    batch._BatchBaseSync__batch_grpc = _BatchGRPC(_ServerVersion.from_string("1.30.0"), None, None)  # type: ignore[attr-defined]
    batch._BatchBaseSync__is_gcp_on_wcd = False  # type: ignore[attr-defined]
    batch._BatchBaseSync__bg_exception = None  # type: ignore[attr-defined]
    batch._BatchBaseSync__reqs = Queue(maxsize=1)  # type: ignore[attr-defined]
    batch._BatchBaseSync__is_hungup = threading.Event()  # type: ignore[attr-defined]
    batch._BatchBaseSync__is_shutting_down = threading.Event()  # type: ignore[attr-defined]
    batch._BatchBaseSync__is_oom = threading.Event()  # type: ignore[attr-defined]
    batch._BatchBaseSync__shutdown_loop = threading.Event()  # type: ignore[attr-defined]
    batch._BatchBaseSync__acks_lock = threading.Lock()  # type: ignore[attr-defined]
    batch._BatchBaseSync__inflight_objs = set()  # type: ignore[attr-defined]
    batch._BatchBaseSync__inflight_refs = set()  # type: ignore[attr-defined]
    batch._BatchBaseSync__stream_generation = 0  # type: ignore[attr-defined]
    batch._BatchBaseSync__generation_lock = threading.Lock()  # type: ignore[attr-defined]
    return batch


def _stream_request(uuid: str) -> _BatchStreamRequest:
    return _BatchStreamRequest(proto=batch_pb2.BatchStreamRequest(), uuids={uuid}, beacons=set())


def test_sync_stale_sender_returns_request_after_fast_reconnect() -> None:
    # regression test for #2261: after a hang-up with a sub-second reconnect,
    # the old stream's sender must not yield the next request into the dead
    # call (gRPC drops it and its uuids wedge __inflight_objs, hanging
    # add_object); it must hand the request back to the live stream's sender
    batch = _make_sync_batch()
    batch._BatchBaseSync__stream_generation = 1  # type: ignore[attr-defined]
    stale = batch._BatchBaseSync__send(1)  # type: ignore[attr-defined]
    assert next(stale).HasField("start")

    # fast reconnect: __recv starts a new stream (generation 2) and clears the
    # hung-up flag before the old sender wakes from its queue wait
    batch._BatchBaseSync__stream_generation = 2  # type: ignore[attr-defined]
    req = _stream_request("uuid-1")
    batch._BatchBaseSync__reqs.put(req)  # type: ignore[attr-defined]

    with pytest.raises(StopIteration):
        next(stale)
    # the request is back on the queue and nothing was marked inflight
    assert batch._BatchBaseSync__reqs.get_nowait() is req  # type: ignore[attr-defined]
    assert batch._BatchBaseSync__inflight_objs == set()  # type: ignore[attr-defined]

    # the live stream's sender delivers the same request exactly once
    batch._BatchBaseSync__reqs.put(req)  # type: ignore[attr-defined]
    live = batch._BatchBaseSync__send(2)  # type: ignore[attr-defined]
    assert next(live).HasField("start")
    assert next(live) is req.proto
    assert batch._BatchBaseSync__inflight_objs == {"uuid-1"}  # type: ignore[attr-defined]


def test_sync_stale_sender_returns_stop_sentinel_after_fast_reconnect() -> None:
    # the None sentinel must also be handed back: if the stale sender consumed
    # it, the live stream would never receive its stop message (#2261)
    batch = _make_sync_batch()
    batch._BatchBaseSync__stream_generation = 1  # type: ignore[attr-defined]
    stale = batch._BatchBaseSync__send(1)  # type: ignore[attr-defined]
    assert next(stale).HasField("start")

    batch._BatchBaseSync__stream_generation = 2  # type: ignore[attr-defined]
    batch._BatchBaseSync__reqs.put(None)  # type: ignore[attr-defined]

    with pytest.raises(StopIteration):
        next(stale)
    assert batch._BatchBaseSync__reqs.get_nowait() is None  # type: ignore[attr-defined]

    batch._BatchBaseSync__reqs.put(None)  # type: ignore[attr-defined]
    live = batch._BatchBaseSync__send(2)  # type: ignore[attr-defined]
    assert next(live).HasField("start")
    assert next(live).HasField("stop")


def _make_async_batch() -> _BatchBaseAsync:
    # async twin of _make_sync_batch, for _BatchBaseAsync.__send/__put_back
    batch = object.__new__(_BatchBaseAsync)
    batch._BatchBaseAsync__batch_grpc = _BatchGRPC(_ServerVersion.from_string("1.30.0"), None, None)  # type: ignore[attr-defined]
    batch._BatchBaseAsync__is_gcp_on_wcd = False  # type: ignore[attr-defined]
    batch._BatchBaseAsync__bg_exception = None  # type: ignore[attr-defined]
    batch._BatchBaseAsync__reqs = asyncio.Queue(maxsize=1)  # type: ignore[attr-defined]
    batch._BatchBaseAsync__is_hungup = asyncio.Event()  # type: ignore[attr-defined]
    batch._BatchBaseAsync__is_shutting_down = asyncio.Event()  # type: ignore[attr-defined]
    batch._BatchBaseAsync__is_oom = asyncio.Event()  # type: ignore[attr-defined]
    batch._BatchBaseAsync__shutdown_loop = asyncio.Event()  # type: ignore[attr-defined]
    batch._BatchBaseAsync__inflight_objs = set()  # type: ignore[attr-defined]
    batch._BatchBaseAsync__inflight_refs = set()  # type: ignore[attr-defined]
    batch._BatchBaseAsync__stream_generation = 0  # type: ignore[attr-defined]
    return batch


@pytest.mark.asyncio
async def test_async_stale_sender_returns_request_after_fast_reconnect() -> None:
    # regression test for #2261, async variant of the sync test above
    batch = _make_async_batch()
    batch._BatchBaseAsync__stream_generation = 1  # type: ignore[attr-defined]
    stale = batch._BatchBaseAsync__send(1)  # type: ignore[attr-defined]
    assert (await anext(stale)).HasField("start")

    batch._BatchBaseAsync__stream_generation = 2  # type: ignore[attr-defined]
    req = _stream_request("uuid-1")
    batch._BatchBaseAsync__reqs.put_nowait(req)  # type: ignore[attr-defined]

    with pytest.raises(StopAsyncIteration):
        await anext(stale)
    assert batch._BatchBaseAsync__reqs.get_nowait() is req  # type: ignore[attr-defined]
    assert batch._BatchBaseAsync__inflight_objs == set()  # type: ignore[attr-defined]

    batch._BatchBaseAsync__reqs.put_nowait(req)  # type: ignore[attr-defined]
    live = batch._BatchBaseAsync__send(2)  # type: ignore[attr-defined]
    assert (await anext(live)).HasField("start")
    assert (await anext(live)) is req.proto
    assert batch._BatchBaseAsync__inflight_objs == {"uuid-1"}  # type: ignore[attr-defined]
