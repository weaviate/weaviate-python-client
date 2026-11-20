"""HTTP-contract tests for replication scale plans."""

import inspect
from functools import partial
from typing import AsyncIterator, Awaitable, TypeVar, Union, cast
from uuid import UUID

import grpc
import pytest
import pytest_asyncio
from pytest_httpserver import HTTPServer

import weaviate
from mock_tests.conftest import MOCK_IP, MOCK_PORT, MOCK_PORT_GRPC
from weaviate.exceptions import WeaviateInvalidInputError, WeaviateUnsupportedFeatureError
from weaviate.outputs.replication import (
    ReplicaAddition,
    ReplicationScaleApplyResult,
    ReplicationScalePlan,
    ShardScaleActions,
)

SCALE_PATH = "/v1/replication/scale"
PLAN_ID = "32536c0e-09e1-4ea1-a2c5-e85af10a9d58"
OPERATION_ID = "47b26ba1-6bc9-41f8-a655-8b9a5b60e1a3"
SECOND_OPERATION_ID = "5fef6289-28d2-4ea2-82a9-48eb501200cd"
Client = Union[weaviate.WeaviateClient, weaviate.WeaviateAsyncClient]
T = TypeVar("T")


@pytest.fixture
def server_version() -> str:
    return "1.35.0"


@pytest.fixture
def weaviate_mock(ready_mock: HTTPServer, server_version: str) -> HTTPServer:
    """Override the shared mock's fixed version for branch-boundary cases."""
    ready_mock.expect_request("/v1/meta").respond_with_json({"version": server_version})
    ready_mock.expect_request("/v1/nodes").respond_with_json(
        {"nodes": [{"name": "node1", "status": "HEALTHY"}]}
    )
    ready_mock.expect_request("/v1/.well-known/openid-configuration").respond_with_json(
        {}, status=404
    )
    return ready_mock


@pytest_asyncio.fixture(params=["sync", "async"])
async def client(
    request: pytest.FixtureRequest,
    weaviate_mock: HTTPServer,
    start_grpc_server: grpc.Server,
) -> AsyncIterator[Client]:
    client: Client
    if request.param == "sync":
        client = weaviate.connect_to_local(host=MOCK_IP, port=MOCK_PORT, grpc_port=MOCK_PORT_GRPC)
    else:
        client = weaviate.use_async_with_local(
            host=MOCK_IP, port=MOCK_PORT, grpc_port=MOCK_PORT_GRPC
        )
        await client.connect()
    try:
        yield client
    finally:
        if isinstance(client, weaviate.WeaviateAsyncClient):
            await client.close()
        else:
            client.close()


async def await_if_needed(value: Union[T, Awaitable[T]]) -> T:
    if inspect.isawaitable(value):
        return await value
    return cast(T, value)


@pytest.mark.asyncio
async def test_generate_scale_plan_request_and_parsing(
    client: Client, weaviate_mock: HTTPServer
) -> None:
    """Capitalize the GET collection and parse ordered additions and omitted addNodes."""
    weaviate_mock.expect_request(
        SCALE_PATH,
        method="GET",
        query_string={"collection": "ArticleArchive", "replicationFactor": "3"},
    ).respond_with_json(
        {
            "planId": PLAN_ID,
            "collection": "ArticleArchive",
            "shardScaleActions": {
                "shard-a": {
                    "removeNodes": ["node4"],
                    "addNodes": {"node3": "node4", "node2": "node1"},
                },
                "shard-b": {"removeNodes": ["node2"]},
            },
        }
    )

    result = await await_if_needed(
        client.cluster.replications.generate_scale_plan(
            collection="articleArchive", replication_factor=3
        )
    )

    assert result == ReplicationScalePlan(
        plan_id=UUID(PLAN_ID),
        collection="ArticleArchive",
        shard_scale_actions={
            "shard-a": ShardScaleActions(
                remove_nodes=["node4"],
                add_nodes=[
                    ReplicaAddition(target_node="node3", source_node="node4"),
                    ReplicaAddition(target_node="node2", source_node="node1"),
                ],
            ),
            "shard-b": ShardScaleActions(remove_nodes=["node2"], add_nodes=[]),
        },
    )
    weaviate_mock.check_assertions()


@pytest.mark.asyncio
async def test_apply_scale_plan_serialization_and_result_parsing(
    client: Client, weaviate_mock: HTTPServer
) -> None:
    """Preserve collection spelling, serialize every shard, and return UUID operation IDs."""
    plan = ReplicationScalePlan(
        plan_id=UUID(PLAN_ID),
        collection="article",
        shard_scale_actions={
            "shard-a": ShardScaleActions(
                remove_nodes=[],
                add_nodes=[
                    ReplicaAddition(target_node="node2", source_node="node1"),
                    ReplicaAddition(target_node="node3", source_node=None),
                ],
            ),
            "shard-b": ShardScaleActions(
                remove_nodes=["node1"],
                add_nodes=[ReplicaAddition(target_node="node2", source_node="node1")],
            ),
            "shard-c": ShardScaleActions(remove_nodes=["node2"], add_nodes=[]),
        },
    )
    weaviate_mock.expect_request(
        SCALE_PATH,
        method="POST",
        json={
            "planId": PLAN_ID,
            "collection": "article",
            "shardScaleActions": {
                "shard-a": {
                    "removeNodes": [],
                    "addNodes": {"node2": "node1", "node3": None},
                },
                "shard-b": {"removeNodes": ["node1"], "addNodes": {"node2": "node1"}},
                "shard-c": {"removeNodes": ["node2"], "addNodes": {}},
            },
        },
    ).respond_with_json(
        {
            "planId": PLAN_ID,
            "collection": "article",
            "operationIds": [OPERATION_ID, SECOND_OPERATION_ID],
        }
    )

    result = await await_if_needed(client.cluster.replications.apply_scale_plan(plan=plan))

    assert result == ReplicationScaleApplyResult(
        plan_id=UUID(PLAN_ID),
        collection="article",
        operation_ids=[UUID(OPERATION_ID), UUID(SECOND_OPERATION_ID)],
    )
    weaviate_mock.check_assertions()


def test_apply_scale_plan_rejects_duplicate_target_nodes(
    weaviate_client: weaviate.WeaviateClient, weaviate_mock: HTTPServer
) -> None:
    """Reject duplicate targets within one shard before making a request."""
    plan = ReplicationScalePlan(
        plan_id=UUID(PLAN_ID),
        collection="Article",
        shard_scale_actions={
            "shard-a": ShardScaleActions(
                remove_nodes=[],
                add_nodes=[
                    ReplicaAddition(target_node="node3", source_node="node1"),
                    ReplicaAddition(target_node="node3", source_node="node2"),
                ],
            )
        },
    )

    weaviate_mock.log.clear()
    with pytest.raises(WeaviateInvalidInputError) as exc:
        weaviate_client.cluster.replications.apply_scale_plan(plan=plan)

    assert "shard-a" in str(exc.value)
    assert "node3" in str(exc.value)
    assert weaviate_mock.log == []


@pytest.mark.parametrize("method", ["GET", "POST"])
@pytest.mark.parametrize(
    ("server_version", "supported"),
    [
        ("1.31.19", False),
        ("1.31.20", True),
        ("1.32.16", False),
        ("1.32.17", True),
        ("1.33.4", False),
        ("1.33.5", True),
        ("1.34.0", False),
        ("1.34.1", True),
    ],
)
def test_scale_methods_enforce_minimum_versions(
    weaviate_client: weaviate.WeaviateClient,
    weaviate_mock: HTTPServer,
    server_version: str,
    supported: bool,
    method: str,
) -> None:
    """Enforce each branch's backport boundary for both public methods."""
    plan = ReplicationScalePlan(plan_id=UUID(PLAN_ID), collection="Article", shard_scale_actions={})
    if method == "GET":
        call = partial(
            weaviate_client.cluster.replications.generate_scale_plan,
            collection="Article",
            replication_factor=3,
        )
        response = {"planId": PLAN_ID, "collection": "Article", "shardScaleActions": {}}
        expected = plan
    else:
        call = partial(weaviate_client.cluster.replications.apply_scale_plan, plan=plan)
        response = {"planId": PLAN_ID, "collection": "Article", "operationIds": []}
        expected = ReplicationScaleApplyResult(
            plan_id=UUID(PLAN_ID), collection="Article", operation_ids=[]
        )

    weaviate_mock.log.clear()
    if supported:
        weaviate_mock.expect_request(SCALE_PATH, method=method).respond_with_json(response)
        assert call() == expected
        assert any(request.path == SCALE_PATH for request, _ in weaviate_mock.log)
        weaviate_mock.check_assertions()
    else:
        with pytest.raises(WeaviateUnsupportedFeatureError) as exc:
            call()
        message = str(exc.value)
        assert server_version in message
        for minimum in ("1.31.20", "1.32.17", "1.33.5", "1.34.1"):
            assert minimum in message
        assert weaviate_mock.log == []
