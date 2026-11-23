import uuid
from typing import Optional

import grpc
import pytest
from pytest_httpserver import HTTPServer

import weaviate
import weaviate.classes as wvc
from mock_tests.conftest import MOCK_IP, MOCK_PORT, MOCK_PORT_GRPC
from weaviate.proto.v1 import batch_delete_pb2, weaviate_pb2_grpc


class _BatchDeleteLimitServicer(weaviate_pb2_grpc.WeaviateServicer):
    def __init__(self, reply: batch_delete_pb2.BatchDeleteReply) -> None:
        self._reply = reply

    def BatchDelete(
        self, request: batch_delete_pb2.BatchDeleteRequest, context: grpc.ServicerContext
    ) -> batch_delete_pb2.BatchDeleteReply:
        return self._reply


def _make_reply(
    *,
    matches: int,
    successful: int,
    verbose: bool,
    limit: Optional[int],
) -> batch_delete_pb2.BatchDeleteReply:
    objects = (
        [
            batch_delete_pb2.BatchDeleteObject(uuid=uuid.uuid4().bytes, successful=True)
            for _ in range(successful)
        ]
        if verbose
        else []
    )
    if limit is None:
        return batch_delete_pb2.BatchDeleteReply(
            failed=0, matches=matches, successful=successful, objects=objects
        )
    return batch_delete_pb2.BatchDeleteReply(
        failed=0, matches=matches, successful=successful, objects=objects, limit=limit
    )


@pytest.mark.parametrize("verbose", [False, True])
@pytest.mark.parametrize(
    ("matches", "successful", "limit"),
    [
        (8, 5, 5),
        (3, 3, 5),
        (0, 0, 0),
        (2, 2, None),
    ],
)
def test_delete_many_limit_sync(
    weaviate_mock: HTTPServer,
    start_grpc_server: grpc.Server,
    verbose: bool,
    matches: int,
    successful: int,
    limit: Optional[int],
) -> None:
    reply = _make_reply(matches=matches, successful=successful, verbose=verbose, limit=limit)
    weaviate_pb2_grpc.add_WeaviateServicer_to_server(
        _BatchDeleteLimitServicer(reply), start_grpc_server
    )

    with weaviate.connect_to_local(
        port=MOCK_PORT, host=MOCK_IP, grpc_port=MOCK_PORT_GRPC
    ) as client:
        ret = client.collections.use("Test").data.delete_many(
            where=wvc.query.Filter.by_property("name").equal("x"),
            verbose=verbose,
        )

    assert ret.matches == matches
    assert ret.successful == successful
    assert ret.failed == 0
    assert ret.limit == limit
    if verbose:
        assert ret.objects is not None
        assert len(ret.objects) == successful
    else:
        assert ret.objects is None


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [5, 0, None])
async def test_delete_many_limit_async(
    weaviate_mock: HTTPServer,
    start_grpc_server: grpc.Server,
    limit: Optional[int],
) -> None:
    reply = _make_reply(matches=8, successful=5, verbose=False, limit=limit)
    weaviate_pb2_grpc.add_WeaviateServicer_to_server(
        _BatchDeleteLimitServicer(reply), start_grpc_server
    )

    async with weaviate.use_async_with_local(
        port=MOCK_PORT, host=MOCK_IP, grpc_port=MOCK_PORT_GRPC
    ) as client:
        ret = await client.collections.use("Test").data.delete_many(
            where=wvc.query.Filter.by_property("name").equal("x"),
        )

    assert ret.matches == 8
    assert ret.successful == 5
    assert ret.limit == limit
