"""Which CA roots the httpx2 clients trust, for origins and for https:// proxies.

httpx2 defaults to the OS trust store; the client pins certifi (as gRPC does), with the
SSL_CERT_FILE/SSL_CERT_DIR overrides httpx honoured under ``trust_env``.
"""

import ssl
import sys
from typing import Any, Dict, List

import certifi
import httpx2
import pytest

import weaviate
import weaviate.connect.base as base_mod
from weaviate.classes.init import AdditionalConfig, Proxies
from weaviate.connect.base import _default_ssl_context, _env_proxy_mounts, _make_proxy

_PROXY_ENV = ("HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "GRPC_PROXY", "grpc_proxy")


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for name in ("SSL_CERT_FILE", "SSL_CERT_DIR", "NO_PROXY", "no_proxy", *_PROXY_ENV):
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


@pytest.fixture
def context_calls(clean_env: pytest.MonkeyPatch) -> List[Dict[str, Any]]:
    """Record the keyword arguments of every ssl.create_default_context call."""
    calls: List[Dict[str, Any]] = []
    real = ssl.create_default_context

    def spy(**kwargs: Any) -> ssl.SSLContext:
        calls.append(kwargs)
        return real()

    clean_env.setattr(base_mod.ssl, "create_default_context", spy)
    return calls


def test_certifi_by_default(context_calls: List[Dict[str, Any]]) -> None:
    assert isinstance(_default_ssl_context(), ssl.SSLContext)
    assert context_calls == [{"cafile": certifi.where()}]


def test_not_the_os_trust_store(clean_env: pytest.MonkeyPatch) -> None:
    truststore = pytest.importorskip("truststore")
    ctx = _default_ssl_context()
    assert isinstance(ctx, ssl.SSLContext)
    assert not isinstance(ctx, truststore.SSLContext)
    certifi_ctx = ssl.create_default_context(cafile=certifi.where())
    assert len(ctx.get_ca_certs()) == len(certifi_ctx.get_ca_certs()) > 0


def test_ssl_cert_file_wins(
    context_calls: List[Dict[str, Any]], clean_env: pytest.MonkeyPatch
) -> None:
    clean_env.setenv("SSL_CERT_FILE", "/certs/ca.pem")
    clean_env.setenv("SSL_CERT_DIR", "/certs")
    _default_ssl_context()
    assert context_calls == [{"cafile": "/certs/ca.pem"}]


def test_ssl_cert_dir_when_no_file(
    context_calls: List[Dict[str, Any]], clean_env: pytest.MonkeyPatch
) -> None:
    clean_env.setenv("SSL_CERT_DIR", "/certs")
    _default_ssl_context()
    assert context_calls == [{"capath": "/certs"}]


def test_env_ignored_without_trust_env(
    context_calls: List[Dict[str, Any]], clean_env: pytest.MonkeyPatch
) -> None:
    clean_env.setenv("SSL_CERT_FILE", "/certs/ca.pem")
    clean_env.setenv("SSL_CERT_DIR", "/certs")
    _default_ssl_context(trust_env=False)
    assert context_calls == [{"cafile": certifi.where()}]


def test_emscripten_keeps_httpx2_default(
    context_calls: List[Dict[str, Any]], clean_env: pytest.MonkeyPatch
) -> None:
    # the browser's fetch verifies TLS
    clean_env.setattr(sys, "platform", "emscripten")
    assert _default_ssl_context() is True
    assert _make_proxy("https://proxy.invalid:3128").ssl_context is None
    assert context_calls == []


def test_http_proxy_gets_no_ssl_context(context_calls: List[Dict[str, Any]]) -> None:
    # httpcore2 rejects a proxy SSL context for the http scheme
    assert _make_proxy("http://proxy.invalid:3128").ssl_context is None
    assert context_calls == []


def test_https_proxy_trusts_certifi(context_calls: List[Dict[str, Any]]) -> None:
    assert isinstance(_make_proxy("https://proxy.invalid:3128").ssl_context, ssl.SSLContext)
    assert context_calls == [{"cafile": certifi.where()}]


def test_https_proxy_follows_trust_env(
    context_calls: List[Dict[str, Any]], clean_env: pytest.MonkeyPatch
) -> None:
    clean_env.setenv("SSL_CERT_FILE", "/certs/ca.pem")
    _make_proxy("https://proxy.invalid:3128", trust_env=False)
    _make_proxy("https://proxy.invalid:3128", trust_env=True)
    assert context_calls == [{"cafile": certifi.where()}, {"cafile": "/certs/ca.pem"}]


def _proxy_ssl_context(transport: Any) -> Any:
    # httpcore2.HTTPProxy keeps the context it hands to the proxy connection
    return transport._pool._proxy_ssl_context


@pytest.mark.parametrize("colour", ["sync", "async"])
def test_configured_https_proxy_trusts_certifi(clean_env: pytest.MonkeyPatch, colour: str) -> None:
    client = weaviate.WeaviateClient(
        connection_params=weaviate.connect.ConnectionParams.from_url(
            "http://localhost:8080", 50051
        ),
        additional_config=AdditionalConfig(
            proxies=Proxies(http="http://proxy.invalid:3128", https="https://proxy.invalid:3129")
        ),
        skip_init_checks=True,
    )
    mounts = client._connection._make_mounts(colour)  # type: ignore[call-overload]
    assert isinstance(_proxy_ssl_context(mounts["https://"]), ssl.SSLContext)
    assert _proxy_ssl_context(mounts["http://"]) is None


@pytest.mark.parametrize("colour", ["sync", "async"])
def test_env_proxy_mounts(clean_env: pytest.MonkeyPatch, colour: str) -> None:
    assert _env_proxy_mounts(colour) == {}  # type: ignore[call-overload]

    clean_env.setenv("HTTP_PROXY", "http://proxy.invalid:3128")
    clean_env.setenv("HTTPS_PROXY", "https://proxy.invalid:3129")
    clean_env.setenv("GRPC_PROXY", "http://proxy.invalid:3130")
    mounts = _env_proxy_mounts(colour)  # type: ignore[call-overload]
    assert set(mounts) == {"http://", "https://"}  # gRPC proxies are not httpx2's business
    assert isinstance(_proxy_ssl_context(mounts["https://"]), ssl.SSLContext)
    assert _proxy_ssl_context(mounts["http://"]) is None


def test_env_proxy_mounts_keep_no_proxy(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("HTTPS_PROXY", "https://proxy.invalid:3129")
    clean_env.setenv("NO_PROXY", "internal.example")
    mounts = _env_proxy_mounts("sync")
    with httpx2.Client(mounts=mounts) as client:
        proxied = client._transport_for_url(httpx2.URL("https://api.github.com"))
        direct = client._transport_for_url(httpx2.URL("https://internal.example"))
    assert proxied is mounts["https://"]
    assert direct is client._transport
