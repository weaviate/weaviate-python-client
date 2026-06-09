import pytest
from pydantic import ValidationError

import weaviate.connect.base as base_mod
from weaviate.connect.base import ConnectionParams


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


def test_from_url_same_host_port_raises_without_prefix() -> None:
    with pytest.raises(ValidationError, match="must be different"):
        ConnectionParams.from_url("http://localhost:8090", grpc_port=8090)


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


def test_different_ports_still_ok_without_prefix() -> None:
    params = ConnectionParams.from_params(
        http_host="localhost",
        http_port=8080,
        http_secure=False,
        grpc_host="localhost",
        grpc_port=50051,
        grpc_secure=False,
    )
    assert params._grpc_web_path_prefix == ""


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


def test_grpc_channel_forwards_path_prefix_option(monkeypatch) -> None:
    captured: dict = {}

    def fake_insecure_channel(target, options=None, **kwargs):
        captured["target"] = target
        captured["options"] = options
        return "CHANNEL"

    monkeypatch.setattr(base_mod.grpc.aio, "insecure_channel", fake_insecure_channel)

    params = ConnectionParams.from_params(
        http_host="localhost",
        http_port=8090,
        http_secure=False,
        grpc_host="localhost",
        grpc_port=8090,
        grpc_secure=False,
        grpc_path_prefix="/grpc-web",
    )
    channel = params._grpc_channel(proxies={}, grpc_msg_size=None, is_async=True)

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
