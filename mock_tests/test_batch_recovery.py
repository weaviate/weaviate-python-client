import json
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from copy import deepcopy

import grpc
import pytest
from grpc_health.v1 import health_pb2, health_pb2_grpc
from werkzeug.wrappers import Response

import weaviate
from weaviate.classes.init import AdditionalConfig, Timeout
from weaviate.classes.config import ConsistencyLevel
from weaviate.proto.v1 import batch_pb2, search_get_pb2, weaviate_pb2_grpc

from .conftest import MOCK_IP, MOCK_PORT_GRPC
from .mock_data import mock_class


def wait_until(predicate, timeout=6):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    assert predicate(), "condition did not become true before deadline"


class RecoveryService(weaviate_pb2_grpc.WeaviateServicer):
    def __init__(self):
        self.lock = threading.Lock()
        self.stream_count = 0
        self.initial_streams = 2
        self.terminated = {}
        self.warm = [threading.Event(), threading.Event()]
        self.fault_go = threading.Event()
        self.recovery_entered = threading.Event()
        self.release = threading.Event()
        self.targets = {1}
        self.phase = "before_ack"
        self.fault_barrier = threading.Barrier(1)
        self.received = Counter()
        self.metadata = []
        self.deadlines = []
        self.retry_failures = 0
        self.retry_failed = threading.Event()
        self.unhealthy = False
        self.node_wait = threading.Event()

    def Search(self, request, context):
        return search_get_pb2.SearchReply()

    def BatchStream(self, request_iterator, context):
        with self.lock:
            self.stream_count += 1
            stream_id = self.stream_count
            ended = self.terminated[stream_id] = threading.Event()
            self.metadata.append(dict(context.invocation_metadata()))
            self.deadlines.append(context.time_remaining())
        context.add_callback(ended.set)
        if stream_id > self.initial_streams:
            self.recovery_entered.set()
            if not self.release.wait(8):
                context.abort(grpc.StatusCode.DEADLINE_EXCEEDED, "test recovery barrier timed out")
            if self.retry_failures:
                self.retry_failures -= 1
                self.retry_failed.set()
                context.abort(grpc.StatusCode.UNAVAILABLE, "temporarily unavailable")
        yield batch_pb2.BatchStreamReply(started=batch_pb2.BatchStreamReply.Started())
        for request in request_iterator:
            if request.HasField("data"):
                uuids = [obj.uuid for obj in request.data.objects.values]
                beacons = [
                    f"weaviate://localhost/{ref.from_collection}/{ref.from_uuid}/{ref.name}"
                    for ref in request.data.references.values
                ]
                with self.lock:
                    self.received.update(uuids)
                    self.received.update(beacons)
                fault = stream_id in self.targets and self.fault_go.is_set()
                if fault:
                    self.fault_barrier.wait(5)
                if fault and self.phase == "before_ack":
                    context.abort(grpc.StatusCode.UNAVAILABLE, "Socket closed")
                yield batch_pb2.BatchStreamReply(
                    acks=batch_pb2.BatchStreamReply.Acks(uuids=uuids, beacons=beacons)
                )
                if fault and self.phase == "after_ack":
                    context.abort(grpc.StatusCode.UNAVAILABLE, "Socket closed")
                yield batch_pb2.BatchStreamReply(
                    results=batch_pb2.BatchStreamReply.Results(
                        successes=[
                            batch_pb2.BatchStreamReply.Results.Success(uuid=uuid) for uuid in uuids
                        ]
                        + [
                            batch_pb2.BatchStreamReply.Results.Success(beacon=beacon)
                            for beacon in beacons
                        ]
                    )
                )
                if fault:
                    context.abort(grpc.StatusCode.UNAVAILABLE, "Socket closed")
                if stream_id <= self.initial_streams:
                    self.warm[stream_id - 1].set()
            if request.HasField("stop"):
                return


class RecoveryHealth(health_pb2_grpc.HealthServicer):
    def __init__(self):
        self.status = None
        self.calls = 0

    def Check(self, request, context):
        self.calls += 1
        if self.status is not None:
            context.abort(self.status, "optional health service unavailable")
        return health_pb2.HealthCheckResponse(status=health_pb2.HealthCheckResponse.SERVING)


@pytest.fixture
def health_service():
    return RecoveryHealth()


@pytest.fixture
def start_grpc_server(health_service):
    with ThreadPoolExecutor(max_workers=10) as executor:
        server = grpc.server(executor)
        health_pb2_grpc.add_HealthServicer_to_server(health_service, server)
        assert server.add_insecure_port(f"[::]:{MOCK_PORT_GRPC}") == MOCK_PORT_GRPC
        server.start()
        try:
            yield server
        finally:
            server.stop(0).wait(5)


@pytest.fixture
def recovery_client(httpserver, start_grpc_server):
    service = RecoveryService()
    metadata_calls = []

    def metadata_handler(request):
        metadata_calls.append(time.monotonic())
        # Expose the old shared-connection reconnect without sleeping arbitrarily.
        if service.fault_go.is_set():
            service.recovery_entered.set()
            if not service.release.wait(8):
                return Response("test metadata barrier timed out", status=503)
        return Response(json.dumps({"version": "1.39.0"}), content_type="application/json")

    httpserver.expect_request("/v1/meta").respond_with_handler(metadata_handler)

    def nodes_handler(request):
        if service.unhealthy:
            service.node_wait.set()
        status = "UNHEALTHY" if service.unhealthy else "HEALTHY"
        return Response(
            json.dumps({"nodes": [{"status": status}, {"status": "HEALTHY"}]}),
            content_type="application/json",
        )

    httpserver.expect_request("/v1/nodes").respond_with_handler(nodes_handler)
    for name in ["Something", "Second"]:
        config = deepcopy(mock_class)
        config["class"] = name
        httpserver.expect_request(f"/v1/schema/{name}").respond_with_json(config)
    weaviate_pb2_grpc.add_WeaviateServicer_to_server(service, start_grpc_server)
    client = weaviate.connect_to_local(
        host=MOCK_IP,
        port=httpserver.port,
        grpc_port=MOCK_PORT_GRPC,
        skip_init_checks=True,
        auth_credentials=weaviate.auth.AuthApiKey("local-test-key"),
        headers={"X-Recovery-Test": "preserved"},
        additional_config=AdditionalConfig(timeout=Timeout(init=3, query=2, insert=2, stream=15)),
    )
    try:
        yield client, service, metadata_calls
    finally:
        service.release.set()
        client.close()
        wait_until(lambda: not [t for t in threading.enumerate() if t.name.startswith("BgBatch")])


@pytest.mark.parametrize("phase", ["before_ack", "after_ack", "after_result"])
@pytest.mark.parametrize("targets", [{1}, {1, 2}])
@pytest.mark.timeout(35)
def test_recovery_preserves_shared_connection_and_replays_unfinished_objects(
    recovery_client, phase, targets
):
    client, service, metadata_calls = recovery_client
    service.phase = phase
    service.targets = targets
    service.fault_barrier = threading.Barrier(len(targets))
    collections = [client.collections.use("Something"), client.collections.use("Second")]
    expected = [set(), set()]
    with ExitStack() as contexts:
        batches = []
        for i, collection in enumerate(collections):
            batch = contexts.enter_context(collection.batch.stream())
            batches.append(batch)
            expected[i].add(batch.add_object({"names": ["warmup"]}))
            assert service.warm[i].wait(5)
        assert collections[0].query.fetch_objects(limit=1).objects == []
        try:
            service.fault_go.set()
            fault_uuids = {}
            for stream_id in targets:
                uuid = batches[stream_id - 1].add_object({"names": ["fault"]})
                expected[stream_id - 1].add(uuid)
                fault_uuids[stream_id] = uuid
            assert service.recovery_entered.wait(6)
            assert client.is_connected()
            assert collections[0].query.fetch_objects(limit=1).objects == []
            assert len(metadata_calls) == 1
            if 2 not in targets:
                assert not service.terminated[2].is_set()
                expected[1].add(batches[1].add_object({"names": ["unaffected"]}))
        finally:
            service.release.set()
        wait_until(lambda: service.stream_count == 2 + len(targets))
        for i, batch in enumerate(batches):
            expected[i].add(batch.add_object({"names": ["after recovery"]}))

    for i, collection in enumerate(collections):
        assert set(collection.batch.results.objs.uuids.values()) == expected[i], service.received
        assert not collection.batch.failed_objects
    for uuid in fault_uuids.values():
        assert service.received[str(uuid)] == (1 if phase == "after_result" else 2)
    assert all(headers["x-recovery-test"] == "preserved" for headers in service.metadata)
    assert all(headers["authorization"] == "Bearer local-test-key" for headers in service.metadata)
    # gRPC's wire deadline rounds slightly, so allow one second of resolution.
    assert all(0 < deadline < 16 for deadline in service.deadlines), service.deadlines
    assert client.is_connected()
    assert collections[0].query.fetch_objects(limit=1).objects == []


@pytest.mark.timeout(30)
def test_close_during_stream_recovery_does_not_reopen_client(recovery_client):
    client, service, metadata_calls = recovery_client
    service.retry_failures = 99
    service.initial_streams = 1
    collection = client.collections.use("Something")
    with collection.batch.stream() as batch:
        batch.add_object({"names": ["warmup"]})
        assert service.warm[0].wait(5)
        service.fault_go.set()
        batch.add_object({"names": ["fault"]})
        try:
            assert service.recovery_entered.wait(6)
        finally:
            service.release.set()
        assert service.retry_failed.wait(5)
        client.close()
        wait_until(lambda: not [t for t in threading.enumerate() if t.name.startswith("BgBatch")])
        assert not client.is_connected()
        assert len(metadata_calls) == 1
    assert not client.is_connected()


@pytest.mark.timeout(30)
def test_consecutive_failures_replay_each_unfinished_object_once(recovery_client):
    client, service, metadata_calls = recovery_client
    service.initial_streams = 1
    service.retry_failures = 2
    collection = client.collections.use("Something")
    with collection.batch.stream() as batch:
        warmup = batch.add_object({"names": ["warmup"]})
        assert service.warm[0].wait(5)
        service.fault_go.set()
        fault = batch.add_object({"names": ["fault"]})
        try:
            assert service.recovery_entered.wait(6)
        finally:
            service.release.set()
        wait_until(lambda: service.stream_count == 4, timeout=10)
        after = batch.add_object({"names": ["after recovery"]})
    assert set(collection.batch.results.objs.uuids.values()) == {warmup, fault, after}
    assert service.received[str(fault)] == 2, service.received
    assert service.received[str(after)] == 1, service.received
    assert not collection.batch.failed_objects
    assert len(metadata_calls) == 1
    assert client.is_connected()


@pytest.mark.parametrize("phase", ["before_ack", "after_ack", "after_result"])
@pytest.mark.timeout(25)
def test_recovery_replays_only_unfinished_references(recovery_client, phase):
    client, service, metadata_calls = recovery_client
    service.initial_streams = 1
    service.phase = phase
    collection = client.collections.use("Something")
    with collection.batch.stream() as batch:
        source = batch.add_object({"names": ["warmup"]})
        assert service.warm[0].wait(5)
        service.fault_go.set()
        batch.add_reference(source, "related", source)
        try:
            assert service.recovery_entered.wait(6)
        finally:
            service.release.set()
        wait_until(lambda: service.stream_count == 2)
        batch.add_reference(source, "other", source)
    beacon = f"weaviate://localhost/Something/{source}/related"
    assert service.received[beacon] == (1 if phase == "after_result" else 2), service.received
    assert service.received[f"weaviate://localhost/Something/{source}/other"] == 1
    assert not collection.batch.failed_references
    assert not collection.batch.results.refs.errors
    assert len(metadata_calls) == 1


@pytest.mark.timeout(25)
def test_recovery_drains_when_context_exits_after_last_object(recovery_client):
    client, service, _ = recovery_client
    service.initial_streams = 1
    service.release.set()
    collection = client.collections.use("Something")
    with collection.batch.stream() as batch:
        warmup = batch.add_object({"names": ["warmup"]})
        assert service.warm[0].wait(5)
        service.fault_go.set()
        fault = batch.add_object({"names": ["fault"]})
    assert set(collection.batch.results.objs.uuids.values()) == {warmup, fault}
    assert service.received[str(fault)] == 2


@pytest.mark.timeout(40)
def test_repeated_failures_stop_only_failed_batch_threads(recovery_client):
    client, service, metadata_calls = recovery_client
    service.initial_streams = 1
    service.retry_failures = 99
    collection = client.collections.use("Something")
    with collection.batch.stream() as batch:
        batch.add_object({"names": ["warmup"]})
        assert service.warm[0].wait(5)
        service.fault_go.set()
        batch.add_object({"names": ["fault"]})
        try:
            assert service.recovery_entered.wait(6)
        finally:
            service.release.set()
        wait_until(
            lambda: not [t for t in threading.enumerate() if t.name.startswith("BgBatch")],
            timeout=25,
        )
        with pytest.raises(weaviate.exceptions.WeaviateBatchStreamError, match="unavailable"):
            batch.add_object({"names": ["cannot be accepted"]})
    assert service.stream_count == 6
    assert client.is_connected()
    assert collection.query.fetch_objects(limit=1).objects == []
    assert len(metadata_calls) == 1


@pytest.mark.timeout(30)
def test_queued_objects_and_references_have_one_replay_owner(recovery_client):
    client, service, _ = recovery_client
    service.initial_streams = 1
    service.retry_failures = 2
    collection = client.collections.use("Something")
    with collection.batch.stream() as batch:
        source = batch.add_object({"names": ["warmup"]})
        assert service.warm[0].wait(5)
        service.fault_go.set()
        fault = batch.add_object({"names": ["fault"]})
        queued = []
        try:
            assert service.recovery_entered.wait(6)
            for i in range(12):
                queued.append(batch.add_object({"names": [f"queued {i}"]}))
                batch.add_reference(source, f"related{i}", source)
        finally:
            service.release.set()
        wait_until(lambda: service.stream_count == 4, timeout=10)
    assert set(collection.batch.results.objs.uuids.values()) == {source, fault, *queued}
    assert service.received[str(fault)] == 2, service.received
    assert all(service.received[str(uuid)] == 1 for uuid in queued), service.received
    for i in range(12):
        assert service.received[f"weaviate://localhost/Something/{source}/related{i}"] == 1
    assert not collection.batch.failed_objects
    assert not collection.batch.failed_references


@pytest.mark.timeout(20)
def test_close_interrupts_wait_for_unhealthy_nodes(recovery_client):
    client, service, metadata_calls = recovery_client
    service.initial_streams = 1
    collection = client.collections.use("Something").with_consistency_level(ConsistencyLevel.ALL)
    with collection.batch.stream() as batch:
        batch.add_object({"names": ["warmup"]})
        assert service.warm[0].wait(5)
        service.unhealthy = True
        service.fault_go.set()
        batch.add_object({"names": ["fault"]})
        assert service.node_wait.wait(5)
        assert client.is_connected()
        assert collection.query.fetch_objects(limit=1).objects == []
        client.close()
        wait_until(lambda: not [t for t in threading.enumerate() if t.name.startswith("BgBatch")])
    assert not client.is_connected()
    assert service.stream_count == 1
    assert len(metadata_calls) == 1


@pytest.mark.parametrize(
    "status", [grpc.StatusCode.UNIMPLEMENTED, grpc.StatusCode.PERMISSION_DENIED]
)
@pytest.mark.timeout(20)
def test_recovery_respects_skip_init_checks(recovery_client, health_service, status):
    client, service, metadata_calls = recovery_client
    health_service.status = status
    service.initial_streams = 1
    service.release.set()
    collection = client.collections.use("Something")
    with collection.batch.stream() as batch:
        warmup = batch.add_object({"names": ["warmup"]})
        assert service.warm[0].wait(5)
        assert collection.query.fetch_objects(limit=1).objects == []
        service.fault_go.set()
        fault = batch.add_object({"names": ["fault"]})
        wait_until(lambda: service.recovery_entered.is_set() or health_service.calls > 0)
        if health_service.calls:
            client.close()
    assert health_service.calls == 0
    assert set(collection.batch.results.objs.uuids.values()) == {warmup, fault}
    assert service.received[str(fault)] == 2
    assert len(metadata_calls) == 1
    assert client.is_connected()
