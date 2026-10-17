from threading import Event
from typing import Any
from unittest.mock import AsyncMock

import grpc
import pytest
from pytest_httpserver import HTTPServer

import weaviate
from mock_tests.conftest import MOCK_IP, MOCK_PORT, MOCK_PORT_GRPC
from weaviate.classes.init import AdditionalConfig, Timeout
from weaviate.collections.classes.grpc import NearMediaType
from weaviate.exceptions import (
    InsufficientPermissionsError,
    WeaviateGenerativeQueryError,
    WeaviateInvalidInputError,
    WeaviateQueryError,
    WeaviateRetryError,
)
from weaviate.proto.v1 import search_get_pb2, weaviate_pb2_grpc


class SearchService(weaviate_pb2_grpc.WeaviateServicer):
    def __init__(self) -> None:
        self.code = grpc.StatusCode.INTERNAL
        self.details = "generative provider failed"
        self.wait_for_deadline = False
        self.requests: list[search_get_pb2.SearchRequest] = []

    def Search(
        self, request: search_get_pb2.SearchRequest, context: grpc.ServicerContext
    ) -> search_get_pb2.SearchReply:
        self.requests.append(request)
        if self.wait_for_deadline:
            cancelled = Event()
            context.add_callback(cancelled.set)
            cancelled.wait(5)
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


async def call(client: Any, namespace: str, method: str, kwargs: dict[str, Any]) -> Any:
    is_async = isinstance(client, weaviate.WeaviateAsyncClient)
    try:
        if is_async:
            await client.connect()
        result = getattr(getattr(client.collections.use("Test"), namespace), method)(**kwargs)
        return await result if is_async else result
    finally:
        if is_async:
            await client.close()
        else:
            client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "method,kwargs",
    [
        ("fetch_objects", {}),
        ("fetch_objects_by_ids", {"ids": ["00000000-0000-0000-0000-000000000001"]}),
        ("bm25", {"query": "test"}),
        ("hybrid", {"query": "test"}),
        ("near_text", {"query": "test"}),
        ("near_vector", {"near_vector": [1.0, 2.0]}),
        ("near_object", {"near_object": "00000000-0000-0000-0000-000000000001"}),
        ("near_image", {"near_image": "aW1hZ2U="}),
        ("near_media", {"media": "YXVkaW8=", "media_type": NearMediaType.AUDIO}),
    ],
)
async def test_generative_query_errors(search_service: SearchService, client, method, kwargs):
    with pytest.raises(WeaviateQueryError) as exc:
        await call(client, "generate", method, {**kwargs, "single_prompt": "Summarize {text}"})
    assert isinstance(exc.value, WeaviateGenerativeQueryError)
    assert exc.value.message == exc.value.error == search_service.details
    assert "GRPC generative search" in str(exc.value)
    assert isinstance(exc.value.__cause__, grpc.RpcError)
    assert search_service.requests[0].HasField("generative")


@pytest.mark.asyncio
@pytest.mark.parametrize("kwargs", [{}, {"grouped_task": "Summarize"}])
@pytest.mark.parametrize("code", [grpc.StatusCode.DEADLINE_EXCEEDED, grpc.StatusCode.UNAVAILABLE])
async def test_generative_timeout_and_retries(
    search_service: SearchService, client, monkeypatch: pytest.MonkeyPatch, kwargs, code
):
    search_service.code = code
    # Exercise the real retry loop and RPCs without waiting through the backoff delays.
    monkeypatch.setattr("weaviate.retry.time.sleep", lambda _: None)
    monkeypatch.setattr("weaviate.retry.asyncio.sleep", AsyncMock())
    with pytest.raises(WeaviateQueryError) as exc:
        await call(client, "generate", "fetch_objects", kwargs)
    assert isinstance(exc.value, WeaviateGenerativeQueryError)
    assert search_service.details in exc.value.error
    assert len(search_service.requests) == (6 if code == grpc.StatusCode.UNAVAILABLE else 1)
    assert isinstance(
        exc.value.__cause__,
        WeaviateRetryError if code == grpc.StatusCode.UNAVAILABLE else grpc.RpcError,
    )


@pytest.mark.asyncio
async def test_generative_client_deadline(search_service: SearchService, client):
    search_service.code = grpc.StatusCode.OK
    search_service.wait_for_deadline = True
    with pytest.raises(WeaviateGenerativeQueryError, match="Deadline Exceeded") as exc:
        await call(client, "generate", "fetch_objects", {"grouped_task": "Summarize"})
    assert isinstance(exc.value, WeaviateQueryError)
    assert len(search_service.requests) == 1


@pytest.mark.asyncio
async def test_generative_validation_is_unchanged(search_service: SearchService, client):
    with pytest.raises(WeaviateInvalidInputError):
        await call(client, "generate", "near_vector", {"near_vector": "invalid"})
    assert search_service.requests == []


@pytest.mark.asyncio
async def test_regular_query_error_is_unchanged(search_service: SearchService, client):
    with pytest.raises(WeaviateQueryError) as exc:
        await call(client, "query", "fetch_objects", {})
    assert type(exc.value) is WeaviateQueryError
    assert exc.value.message == exc.value.error == search_service.details
    assert str(exc.value) == (
        f"Query call with protocol GRPC search failed with message {search_service.details}."
    )
    assert not search_service.requests[0].HasField("generative")


@pytest.mark.asyncio
async def test_generative_permissions_are_unchanged(search_service: SearchService, client):
    search_service.code = grpc.StatusCode.PERMISSION_DENIED
    with pytest.raises(InsufficientPermissionsError):
        await call(client, "generate", "fetch_objects", {"grouped_task": "Summarize"})


@pytest.mark.asyncio
async def test_successful_generative_query(search_service: SearchService, client):
    search_service.code = grpc.StatusCode.OK
    result = await call(client, "generate", "fetch_objects", {"grouped_task": "Summarize"})
    assert result.objects == []
