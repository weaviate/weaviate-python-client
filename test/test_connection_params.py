import sys

import pytest
from pydantic import ValidationError

import weaviate.connect.base as base_mod
from weaviate.connect.base import ConnectionParams
from weaviate.exceptions import WeaviateInvalidInputError


def test_same_host_port_raises_without_prefix() -> None:
    with pytest.raises(ValidationError, match="must be different"):
        ConnectionParams.from_params(
            http_host="localhost",
            http_port=8090,
            http_secure=False,
            grpc_host="localhost",
            grpc_port=8090,
            grpc_secure=False,
        )


def test_same_host_port_allowed_with_grpc_web_prefix() -> None:
    params = ConnectionParams.from_params(
        http_host="localhost",
        http_port=8090,
        http_secure=False,
        grpc_host="localhost",
        grpc_port=8090,
        grpc_secure=False,
        grpc_path_prefix="/grpc-web",
    )
    assert params._grpc_web_path_prefix == "/grpc-web"


def test_from_url_same_host_port_allowed_with_prefix() -> None:
    params = ConnectionParams.from_url(
        "http://localhost:8090", grpc_port=8090, grpc_path_prefix="/grpc-web"
    )
    assert params._grpc_web_path_prefix == "/grpc-web"


@pytest.mark.parametrize(
    "raw,expected",
    [
        (None, ""),
        ("", ""),
        ("/", ""),
        ("grpc-web", "/grpc-web"),
        ("/grpc-web", "/grpc-web"),
        ("grpc-web/", "/grpc-web"),
        ("/a/b/", "/a/b"),
    ],
)
def test_path_prefix_normalization(raw, expected) -> None:
    params = ConnectionParams.from_params(
        http_host="h",
        http_port=8080,
        http_secure=False,
        grpc_host="g",
        grpc_port=50051,
        grpc_secure=False,
        grpc_path_prefix=raw,
    )
    assert params._grpc_web_path_prefix == expected


def _grpc_web_params() -> ConnectionParams:
    return ConnectionParams.from_params(
        http_host="localhost",
        http_port=8090,
        http_secure=False,
        grpc_host="localhost",
        grpc_port=8090,
        grpc_secure=False,
        grpc_path_prefix="/grpc-web",
    )


def test_grpc_channel_forwards_path_prefix_option(monkeypatch) -> None:
    captured: dict = {}

    def fake_insecure_channel(target, options=None, **kwargs):
        captured["target"] = target
        captured["options"] = options
        return "CHANNEL"

    monkeypatch.setattr(base_mod.grpc.aio, "insecure_channel", fake_insecure_channel)

    channel = _grpc_web_params()._grpc_channel(proxies={}, grpc_msg_size=None, is_async=True)

    assert channel == "CHANNEL"
    assert captured["target"] == "localhost:8090"
    assert ("grpc-web.path_prefix", "/grpc-web") in captured["options"]


def test_grpc_channel_omits_option_without_prefix(monkeypatch) -> None:
    captured: dict = {}

    def fake_insecure_channel(target, options=None, **kwargs):
        captured["options"] = options
        return "CHANNEL"

    monkeypatch.setattr(base_mod.grpc.aio, "insecure_channel", fake_insecure_channel)

    params = ConnectionParams.from_params(
        http_host="localhost",
        http_port=8080,
        http_secure=False,
        grpc_host="localhost",
        grpc_port=50051,
        grpc_secure=False,
    )
    params._grpc_channel(proxies={}, grpc_msg_size=None, is_async=True)

    option_keys = [key for key, _ in captured["options"]]
    assert "grpc-web.path_prefix" not in option_keys


def test_async_client_construction_rejects_prefix_without_shim(monkeypatch) -> None:
    # fail at construction with actionable text, not deep inside connect() after the
    # OIDC and /v1/meta round trips already succeeded
    from weaviate import WeaviateAsyncClient

    monkeypatch.delattr(base_mod.grpc, "__weaviate_client_web_shim__", raising=False)
    with pytest.raises(WeaviateInvalidInputError, match="weaviate-client-web"):
        WeaviateAsyncClient(_grpc_web_params())


def test_async_client_construction_allows_prefix_with_shim(monkeypatch) -> None:
    from weaviate import WeaviateAsyncClient

    monkeypatch.setattr(base_mod.grpc, "__weaviate_client_web_shim__", True, raising=False)
    client = WeaviateAsyncClient(_grpc_web_params())
    assert client._connection._connection_params._grpc_web_path_prefix == "/grpc-web"


def test_sync_client_construction_rejects_grpc_web_prefix() -> None:
    from weaviate import WeaviateClient

    with pytest.raises(WeaviateInvalidInputError, match="async"):
        WeaviateClient(_grpc_web_params())


@pytest.mark.parametrize(
    "call,expected",
    [
        (
            lambda w: w.use_async_with_local(),
            {
                "http": {"host": "localhost", "port": 8080, "secure": False},
                "grpc": {"host": "localhost", "port": 50051, "secure": False},
                "grpc_path_prefix": None,
            },
        ),
        (
            lambda w: w.use_async_with_weaviate_cloud("abc.something.weaviate.cloud", None),
            {
                "http": {"host": "abc.something.weaviate.cloud", "port": 443, "secure": True},
                "grpc": {"host": "grpc-abc.something.weaviate.cloud", "port": 443, "secure": True},
                "grpc_path_prefix": None,
            },
        ),
        (
            lambda w: w.use_async_with_custom(
                http_host="rest.example.com",
                http_port=443,
                http_secure=True,
                grpc_host="grpc.example.com",
                grpc_port=443,
                grpc_secure=True,
            ),
            {
                "http": {"host": "rest.example.com", "port": 443, "secure": True},
                "grpc": {"host": "grpc.example.com", "port": 443, "secure": True},
                "grpc_path_prefix": None,
            },
        ),
    ],
)
def test_helper_params_off_emscripten_are_unchanged(call, expected) -> None:
    # the no-regression pin: off Emscripten the helpers build exactly the params they
    # always did; grpc_path_prefix is new and stays None (native gRPC)
    import weaviate

    assert sys.platform != "emscripten"
    params = call(weaviate)._connection._connection_params
    assert params.model_dump() == expected
    assert params._grpc_web_path_prefix == ""
