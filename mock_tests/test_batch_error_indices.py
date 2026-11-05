"""`BatchObjectReturn.errors` must be keyed by the original batch index on every path.

`BatchObjectReturn.__add__` merges chunk results with a plain `dict.update`, so the
wholesale-failure path in `_BatchBase.__send_batch` has to key its errors by
`obj.index` like the success path does. Keying them by the position inside the chunk
makes the keys of different chunks collide.
"""

from typing import List

import grpc
import pytest
import weaviate
from weaviate.proto.v1 import batch_pb2, weaviate_pb2_grpc

from .conftest import MOCK_IP, MOCK_PORT, MOCK_PORT_GRPC, mock_class


class MockChunkedService(weaviate_pb2_grpc.WeaviateServicer):
    """Answers each `BatchObjects` call according to `per_chunk`, a list of bools."""

    def __init__(self, per_chunk: List[bool]) -> None:
        self.per_chunk = per_chunk
        self.calls: List[List[str]] = []

    def BatchObjects(
        self, request: batch_pb2.BatchObjectsRequest, context: grpc.ServicerContext
    ) -> batch_pb2.BatchObjectsReply:
        index = len(self.calls)
        self.calls.append([str(obj.uuid) for obj in request.objects])
        if self.per_chunk[index]:
            return batch_pb2.BatchObjectsReply()
        return batch_pb2.BatchObjectsReply(
            errors=[
                {"index": i, "error": f"mock rejection {i}"} for i in range(len(request.objects))
            ]
        )


def _client_with(service, weaviate_mock, start_grpc_server):
    weaviate_mock.expect_request(f"/v1/schema/{mock_class['class']}").respond_with_json(mock_class)
    weaviate_pb2_grpc.add_WeaviateServicer_to_server(service, start_grpc_server)
    return weaviate.connect_to_local(port=MOCK_PORT, host=MOCK_IP, grpc_port=MOCK_PORT_GRPC)


@pytest.fixture
def make_client(weaviate_mock, start_grpc_server):
    clients = []

    def _make(per_chunk: List[bool]):
        service = MockChunkedService(per_chunk)
        client = _client_with(service, weaviate_mock, start_grpc_server)
        clients.append(client)
        return client, service

    yield _make
    for client in clients:
        client.close()


def _add_objects(collection, count: int) -> List:
    uuids = []
    with collection.batch.fixed_size(batch_size=2, concurrent_requests=1) as batch:
        for i in range(count):
            uuids.append(batch.add_object({"name": f"Object {i}"}))
        batch.flush()
    return uuids


def test_wholesale_failed_chunks_report_every_object(make_client):
    client, service = make_client([False, False])
    collection = client.collections.use(mock_class["class"])

    _add_objects(collection, 4)

    assert len(service.calls) == 2, "the 4 objects must be split into two chunks"

    errors = collection.batch.results.objs.errors
    assert sorted(errors) == [0, 1, 2, 3], (
        f"every failed object must be reported once, got {sorted(errors)}"
    )
    for index, error in errors.items():
        assert error.object_.index == index, (
            f"errors[{index}] describes the object at index {error.object_.index}"
        )
    assert len(collection.batch.failed_objects) == len(errors)


def test_failed_and_successful_chunks_do_not_share_keys(make_client):
    client, service = make_client([True, False])
    collection = client.collections.use(mock_class["class"])

    uuids = _add_objects(collection, 4)

    assert len(service.calls) == 2
    result = collection.batch.results.objs
    assert sorted(result.uuids) == [0, 1]
    assert sorted(result.errors) == [2, 3], (
        f"the failed chunk must be reported under its own indices, got {sorted(result.errors)}"
    )
    assert not set(result.uuids) & set(result.errors), (
        "a key cannot describe both an inserted and a failed object"
    )
    for index in result.errors:
        assert str(result.errors[index].object_.uuid) == str(uuids[index])


def test_successful_chunks_keep_original_indices(make_client):
    client, service = make_client([True, True, True])
    collection = client.collections.use(mock_class["class"])

    uuids = _add_objects(collection, 6)

    assert len(service.calls) == 3
    result = collection.batch.results.objs
    assert sorted(result.uuids) == [0, 1, 2, 3, 4, 5]
    for index, uuid in enumerate(uuids):
        assert str(result.uuids[index]) == str(uuid)
