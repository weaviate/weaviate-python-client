from typing import Any
from unittest.mock import AsyncMock

import grpc
import pytest
from pytest_httpserver import HTTPServer

import weaviate
from mock_tests.conftest import MOCK_IP, MOCK_PORT, MOCK_PORT_GRPC
from weaviate.classes.init import AdditionalConfig, Timeout
from weaviate.exceptions import (
    InsufficientPermissionsError,
    WeaviateGenerativeQueryError,
)
from weaviate.proto.v1 import search_get_pb2, weaviate_pb2_grpc


class SearchService(weaviate_pb2_grpc.WeaviateServicer):
    def __init__(self) -> None:
        self.code = grpc.StatusCode.INTERNAL
        self.details = "generative provider failed"
        self.requests: list[search_get_pb2.SearchRequest] = []

    def Search(
        self, request: search_get_pb2.SearchRequest, context: grpc.ServicerContext
    ) -> search_get_pb2.SearchReply:
        self.requests.append(request)
        if self.code != grpc.StatusCode.OK:
            context.abort(self.code, self.details)
        return search_get_pb2.SearchReply()


@pytest.fixture
def search_service(start_grpc_server: grpc.Server) -> SearchService:
    service = SearchService()
    weaviate_pb2_grpc.add_WeaviateServicer_to_server(service, start_grpc_server)
    return service


@pytest.fixture(params=[False, True], ids=["sync", "async"])
def client(request: pytest.FixtureRequest, weaviate_mock: HTTPServer):
    factory = weaviate.use_async_with_local if request.param else weaviate.connect_to_local
    return factory(
        host=MOCK_IP,
        port=MOCK_PORT,
        grpc_port=MOCK_PORT_GRPC,
        skip_init_checks=True,
        additional_config=AdditionalConfig(timeout=Timeout(query=1)),
    )


async def call(client: Any, grouped_task: str) -> None:
    is_async = isinstance(client, weaviate.WeaviateAsyncClient)
    try:
        if is_async:
            await client.connect()
        result = client.collections.use("Test").generate.fetch_objects(grouped_task=grouped_task)
        if is_async:
            await result
    finally:
        if is_async:
            await client.close()
        else:
            client.close()


@pytest.mark.asyncio
async def test_generative_retry_error(
    search_service: SearchService, client: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    search_service.code = grpc.StatusCode.UNAVAILABLE
    monkeypatch.setattr("weaviate.retry.time.sleep", lambda _: None)
    monkeypatch.setattr("weaviate.retry.asyncio.sleep", AsyncMock())
    with pytest.raises(WeaviateGenerativeQueryError) as exc:
        await call(client, "Summarize")
    assert search_service.details in exc.value.error
    assert len(search_service.requests) == 6
    assert all(request.HasField("generative") for request in search_service.requests)


@pytest.mark.asyncio
async def test_generative_permissions_are_unchanged(
    search_service: SearchService, client: Any
) -> None:
    search_service.code = grpc.StatusCode.PERMISSION_DENIED
    with pytest.raises(InsufficientPermissionsError):
        await call(client, "Summarize")
