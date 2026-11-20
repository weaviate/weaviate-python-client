import threading
import uuid as uuid_package
from decimal import Decimal
from typing import AsyncGenerator, Dict, Generator, List

import grpc
import pytest
import pytest_asyncio
import weaviate
from weaviate.collections.batch.async_ import _BatchBaseAsync
from weaviate.collections.batch.base import _BatchDataWrapper
from weaviate.collections.batch.grpc_batch import _BatchGRPC
from weaviate.collections.batch.sync import _BatchBaseSync
from weaviate.collections.classes.batch import BatchObject, _BatchObject
from weaviate.exceptions import WeaviateInsertManyAllFailedError
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


# --- regression tests for #2266: one unencodable object must not fail the batch ---


def _internal_obj(i: int, bad: bool = False) -> _BatchObject:
    props: Dict[str, object] = {"name": f"Object {i}"}
    if bad:
        # a Decimal property cannot be encoded into a protobuf Struct on main
        props["price"] = Decimal("1.5")
    return _BatchObject(
        collection="Test",
        properties=props,  # type: ignore[arg-type]
        references={},
        uuid=str(uuid_package.uuid4()),
        vector=None,
        tenant=None,
        index=i,
    )


class _StubConnection:
    def __init__(self, errors: Dict[int, str] | None = None) -> None:
        self.received: int | None = None
        self._errors = errors or {}

    def grpc_batch_objects(self, request, timeout, max_retries):  # noqa: ANN001, ANN202
        self.received = len(request.objects)
        return self._errors


def test_grpc_objects_one_unencodable_object_does_not_fail_the_batch() -> None:
    grpc_batch = _BatchGRPC(_ServerVersion.from_string("1.40.0"), None, None)
    objs = [_internal_obj(i, bad=(i == 37)) for i in range(100)]
    conn = _StubConnection()
    res = grpc_batch.objects(connection=conn, objects=objs, timeout=10, max_retries=0)  # type: ignore[arg-type]
    assert conn.received == 99
    assert len(res.uuids) == 99
    assert list(res.errors.keys()) == [37]
    assert str(objs[37].uuid) in res.errors[37].message
    assert res.has_errors


def test_grpc_objects_server_error_is_translated_past_an_encoding_failure() -> None:
    # object 0 fails to encode, so the server's error at request position 0
    # belongs to the caller's object 1, not object 0
    grpc_batch = _BatchGRPC(_ServerVersion.from_string("1.40.0"), None, None)
    objs = [_internal_obj(i, bad=(i == 0)) for i in range(3)]
    conn = _StubConnection(errors={0: "server error"})
    res = grpc_batch.objects(connection=conn, objects=objs, timeout=10, max_retries=0)  # type: ignore[arg-type]
    assert conn.received == 2
    assert sorted(res.errors.keys()) == [0, 1]
    assert res.errors[1].message == "server error"
    assert list(res.uuids.keys()) == [2]


def test_grpc_objects_all_unencodable_raises_all_failed() -> None:
    grpc_batch = _BatchGRPC(_ServerVersion.from_string("1.40.0"), None, None)
    objs = [_internal_obj(i, bad=True) for i in range(3)]
    conn = _StubConnection()
    with pytest.raises(WeaviateInsertManyAllFailedError):
        grpc_batch.objects(connection=conn, objects=objs, timeout=10, max_retries=0)  # type: ignore[arg-type]
    assert conn.received is None


def _batch_object(i: int, bad: bool = False) -> BatchObject:
    props: Dict[str, object] = {"name": f"Object {i}"}
    if bad:
        props["price"] = Decimal("1.5")
    return BatchObject(
        collection="Test",
        properties=props,  # type: ignore[arg-type]
        references=None,
        uuid=uuid_package.uuid4(),
        vector=None,
        tenant=None,
        index=i,
    )


def test_sync_stream_skips_unencodable_object_and_records_error() -> None:
    batch = object.__new__(_BatchBaseSync)
    batch._BatchBaseSync__batch_grpc = _BatchGRPC(  # type: ignore[attr-defined]
        _ServerVersion.from_string("1.40.0"), None, None
    )
    objs = [_batch_object(i, bad=(i == 1)) for i in range(3)]
    batch._BatchBaseSync__objs_cache = {str(o.uuid): o for o in objs}  # type: ignore[attr-defined]
    batch._BatchBaseSync__uuid_lookup = {str(o.uuid) for o in objs}  # type: ignore[attr-defined]
    batch._BatchBaseSync__objs_cache_lock = threading.Lock()  # type: ignore[attr-defined]
    batch._BatchBaseSync__uuid_lookup_lock = threading.Lock()  # type: ignore[attr-defined]
    batch._BatchBaseSync__results_lock = threading.Lock()  # type: ignore[attr-defined]
    batch._BatchBaseSync__results_for_wrapper = _BatchDataWrapper()  # type: ignore[attr-defined]

    requests = list(batch._BatchBaseSync__generate_stream_requests(objs, []))  # type: ignore[attr-defined]
    sent = [o for req in requests for o in req.proto.data.objects.values]
    assert len(sent) == 2

    wrapper = batch._BatchBaseSync__results_for_wrapper  # type: ignore[attr-defined]
    assert len(wrapper.failed_objects) == 1
    assert wrapper.failed_objects[0].object_.index == 1
    assert str(objs[1].uuid) in wrapper.failed_objects[0].message
    assert str(objs[1].uuid) not in batch._BatchBaseSync__objs_cache  # type: ignore[attr-defined]
    assert str(objs[1].uuid) not in batch._BatchBaseSync__uuid_lookup  # type: ignore[attr-defined]


def test_async_stream_skips_unencodable_object_and_records_error() -> None:
    batch = object.__new__(_BatchBaseAsync)
    batch._BatchBaseAsync__batch_grpc = _BatchGRPC(  # type: ignore[attr-defined]
        _ServerVersion.from_string("1.40.0"), None, None
    )
    objs = [_batch_object(i, bad=(i == 1)) for i in range(3)]
    batch._BatchBaseAsync__objs_cache = {str(o.uuid): o for o in objs}  # type: ignore[attr-defined]
    batch._BatchBaseAsync__uuid_lookup = {str(o.uuid) for o in objs}  # type: ignore[attr-defined]
    batch._BatchBaseAsync__results_for_wrapper = _BatchDataWrapper()  # type: ignore[attr-defined]

    requests = list(batch._BatchBaseAsync__generate_stream_requests(objs, []))  # type: ignore[attr-defined]
    sent = [o for req in requests for o in req.proto.data.objects.values]
    assert len(sent) == 2

    wrapper = batch._BatchBaseAsync__results_for_wrapper  # type: ignore[attr-defined]
    assert len(wrapper.failed_objects) == 1
    assert wrapper.failed_objects[0].object_.index == 1
    assert str(objs[1].uuid) not in batch._BatchBaseAsync__objs_cache  # type: ignore[attr-defined]
