import pytest

from weaviate.auth import AuthApiKey
from weaviate.client import WeaviateAsyncClient, WeaviateClient
from weaviate.connect import helpers


def _assert_string_api_key(client: WeaviateClient | WeaviateAsyncClient) -> None:
    assert isinstance(client._connection._auth, AuthApiKey)
    assert client._connection._auth.api_key == "api-key"


def test_connect_to_custom_accepts_string_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(helpers, "__connect", lambda client: client)

    client = helpers.connect_to_custom(
        http_host="localhost",
        http_port=8080,
        http_secure=False,
        grpc_host="localhost",
        grpc_port=50051,
        grpc_secure=False,
        auth_credentials="api-key",
    )

    _assert_string_api_key(client)


def test_use_async_with_weaviate_cloud_accepts_string_api_key() -> None:
    client = helpers.use_async_with_weaviate_cloud(
        cluster_url="example.weaviate.network",
        auth_credentials="api-key",
    )

    _assert_string_api_key(client)


def test_use_async_with_custom_accepts_string_api_key() -> None:
    client = helpers.use_async_with_custom(
        http_host="localhost",
        http_port=8080,
        http_secure=False,
        grpc_host="localhost",
        grpc_port=50051,
        grpc_secure=False,
        auth_credentials="api-key",
    )

    _assert_string_api_key(client)
