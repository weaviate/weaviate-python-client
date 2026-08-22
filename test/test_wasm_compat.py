"""Unit tests for WASM/Pyodide-compatibility behaviour that runs on CPython too.

Under Emscripten there are no subprocesses, no threads and no sockets — these tests pin
the guards, the grpc-web auto-routing and the grpc-web diagnostics added for that
environment without needing a browser.
"""

import asyncio
import sys

import grpc
import pytest
from grpc.aio import AioRpcError, Metadata

from weaviate import WeaviateClient
from weaviate.collections.batch.async_ import _BatchBaseAsync
from weaviate.connect.base import ConnectionParams
from weaviate.connect.v4 import _ConnectionBase
from weaviate.embedded import _EmbeddedBase
from weaviate.exceptions import (
    WeaviateBatchStreamError,
    WeaviateGRPCUnavailableError,
    WeaviateStartUpError,
)
from weaviate.util import _ServerVersion


def test_embedded_raises_explicit_error_under_emscripten(monkeypatch) -> None:
    # without the guard, the Emscripten socket emulation makes the port probe
    # "succeed" and embedded misreports that Weaviate is already listening
    monkeypatch.setattr(sys, "platform", "emscripten")
    with pytest.raises(WeaviateStartUpError, match="WebAssembly/Pyodide"):
        _EmbeddedBase.check_supported_platform()


def test_sync_client_construction_raises_async_only_under_emscripten(monkeypatch) -> None:
    # without the guard the sync client constructs fine and the first REST call fails
    # with an opaque ConnectError; the clear async-only error must win, at construction
    monkeypatch.setattr(sys, "platform", "emscripten")
    with pytest.raises(WeaviateStartUpError, match="async client"):
        WeaviateClient(connection_params=ConnectionParams.from_url("http://localhost:8080", 50051))


def test_batch_stream_fails_fast_when_grpc_web_shim_active(monkeypatch) -> None:
    # over grpc-web the BatchStream RPC would die inside the background tasks (silent
    # drop / endless flush); _start must raise before any task is created
    monkeypatch.setattr(grpc, "__weaviate_client_web_shim__", True, raising=False)
    batch = object.__new__(_BatchBaseAsync)  # the guard runs before any attribute access
    with pytest.raises(WeaviateBatchStreamError, match="insert_many"):
        asyncio.run(batch._start())


# --- grpc-web diagnostics -------------------------------------------------------------


def _connection(prefix=None) -> _ConnectionBase:
    conn = object.__new__(_ConnectionBase)
    conn._client = None
    conn._grpc_channel = None
    conn._weaviate_version = _ServerVersion.from_string("1.36.0")
    conn._connection_params = ConnectionParams.from_url(
        "http://localhost:8080",
        grpc_port=8080 if prefix else 50051,
        grpc_path_prefix=prefix,
    )
    return conn


def _ping_exception(conn: _ConnectionBase, error: Exception) -> None:
    getattr(conn, "_ConnectionBase__handle_ping_exception")(error)  # noqa: B009


def test_grpc_web_404_names_the_two_real_causes_and_drops_firewall_advice() -> None:
    # over grpc-web there is no separate gRPC port and no firewall: REST just succeeded
    # against this very host:port. A 404 means the path was not routed.
    conn = _connection(prefix="/grpc-web")
    error = AioRpcError(
        grpc.StatusCode.UNIMPLEMENTED,
        Metadata(),
        Metadata(),
        details="HTTP 404 for /grpc-web/grpc.health.v1.Health/Check: 404 page not found",
    )
    with pytest.raises(WeaviateGRPCUnavailableError) as excinfo:
        _ping_exception(conn, error)
    msg = str(excinfo.value)

    assert "firewall" not in msg
    assert "port (localhost:8080) are correct" not in msg
    assert "UNIMPLEMENTED" in msg  # the real code, not swallowed
    assert "HTTP 404 for /grpc-web/grpc.health.v1.Health/Check" in msg  # ... and details
    assert "/grpc-web" in msg  # the prefix that was actually used
    assert "1.38.3" in msg  # candidate 1: server too old ...
    assert "v1.36.0" in msg  # ... shown against the observed server version
    assert "/v1/grpc-web" in msg  # candidate 2: wrong prefix


def test_grpc_web_non_404_error_still_omits_the_native_port_advice() -> None:
    conn = _connection(prefix="/grpc-web")
    error = AioRpcError(
        grpc.StatusCode.UNAVAILABLE, Metadata(), Metadata(), details="HTTP 502 for /grpc-web/..."
    )
    with pytest.raises(WeaviateGRPCUnavailableError) as excinfo:
        _ping_exception(conn, error)
    msg = str(excinfo.value)

    assert "firewall" not in msg
    assert "UNAVAILABLE" in msg
    assert "HTTP 502" in msg
    assert "skip_init_checks=True" in msg  # the still-useful advice is kept


def test_native_grpc_message_keeps_its_advice_and_gains_the_real_status() -> None:
    conn = _connection()
    error = AioRpcError(
        grpc.StatusCode.UNAVAILABLE, Metadata(), Metadata(), details="failed to connect"
    )
    with pytest.raises(WeaviateGRPCUnavailableError) as excinfo:
        _ping_exception(conn, error)
    msg = str(excinfo.value)

    # unchanged guidance for native gRPC ...
    assert "The gRPC traffic at the specified port is blocked by a firewall." in msg
    assert "Please check that the server address and port (localhost:50051) are correct." in msg
    # ... plus the error that was previously discarded
    assert "UNAVAILABLE" in msg
    assert "failed to connect" in msg


def test_non_grpc_ping_error_is_still_reported() -> None:
    # not every ping failure is an RpcError; those must not lose the generic advice
    conn = _connection()
    with pytest.raises(WeaviateGRPCUnavailableError) as excinfo:
        _ping_exception(conn, ValueError("boom"))
    assert "blocked by a firewall" in str(excinfo.value)


# --- grpc-web auto-routing under Emscripten -------------------------------------------
#
# Native gRPC is impossible under WASM (no sockets, no grpcio wheel), so the async connect
# helpers pin gRPC to the REST endpoint under Weaviate's own grpc-web base path — the same
# contract as the TypeScript @weaviate/web client's webify(). Nothing selects it.

GRPC_WEB_PREFIX = "/v1/grpc-web"


@pytest.fixture
def emscripten(monkeypatch):
    """Fake Emscripten, with the grpc-web shim marked active.

    Under real Pyodide ``import weaviate`` installs the shim itself; here only the
    routing decision is under test, not the environment check that guards it.
    """
    import weaviate.connect.base as base_mod

    monkeypatch.setattr(sys, "platform", "emscripten")
    monkeypatch.setattr(base_mod.grpc, "__weaviate_client_web_shim__", True, raising=False)


def _params(client) -> ConnectionParams:
    return client._connection._connection_params


def _assert_grpc_rides_rest(client) -> None:
    params = _params(client)
    assert params.grpc.model_dump() == params.http.model_dump()
    assert params._grpc_web_path_prefix == GRPC_WEB_PREFIX
    assert params._grpc_target == f"{params.http.host}:{params.http.port}"


def test_use_async_with_local_routes_grpc_to_rest_under_emscripten(emscripten) -> None:
    import weaviate

    _assert_grpc_rides_rest(weaviate.use_async_with_local(host="localhost", port=8290))
    assert _params(weaviate.use_async_with_local()).model_dump() == {
        "http": {"host": "localhost", "port": 8080, "secure": False},
        "grpc": {"host": "localhost", "port": 8080, "secure": False},
        "grpc_path_prefix": GRPC_WEB_PREFIX,
    }


def test_use_async_with_weaviate_cloud_routes_grpc_to_the_cluster_host(emscripten) -> None:
    # WCD serves grpc-web on the cluster's own REST endpoint, not on grpc-<cluster>
    import weaviate

    client = weaviate.use_async_with_weaviate_cloud("abc.something.weaviate.cloud", None)
    _assert_grpc_rides_rest(client)
    assert _params(client).model_dump() == {
        "http": {"host": "abc.something.weaviate.cloud", "port": 443, "secure": True},
        "grpc": {"host": "abc.something.weaviate.cloud", "port": 443, "secure": True},
        "grpc_path_prefix": GRPC_WEB_PREFIX,
    }


def test_use_async_with_custom_routes_grpc_to_rest_under_emscripten(emscripten) -> None:
    import weaviate

    _assert_grpc_rides_rest(
        weaviate.use_async_with_custom(
            http_host="wv.example.com",
            http_port=443,
            http_secure=True,
            grpc_host="wv.example.com",
            grpc_port=443,
            grpc_secure=True,
        )
    )


def test_matching_grpc_arguments_are_not_warned_about(emscripten, recwarn) -> None:
    # the documented WASM shape: gRPC arguments equal to the HTTP ones. Nothing is
    # discarded, so warning here would just train users to ignore the warning.
    import weaviate

    weaviate.use_async_with_custom(
        http_host="localhost",
        http_port=8290,
        http_secure=False,
        grpc_host="localhost",
        grpc_port=8290,
        grpc_secure=False,
    )
    weaviate.use_async_with_local(port=8290)
    weaviate.use_async_with_weaviate_cloud("abc.something.weaviate.cloud", None)
    assert [str(w.message) for w in recwarn] == []


def test_overridden_grpc_arguments_are_warned_about(emscripten) -> None:
    # Python cannot drop required parameters the way TypeScript drops them from a type,
    # so a WASM caller must pass something. Overriding keeps the client usable, but it
    # must never look like the endpoint they gave was honoured.
    import weaviate

    with pytest.warns(UserWarning, match="Con006") as record:
        client = weaviate.use_async_with_custom(
            http_host="localhost",
            http_port=8080,
            http_secure=False,
            grpc_host="grpc.example.com",
            grpc_port=50051,
            grpc_secure=True,
        )
    msg = str(record[0].message)
    assert "grpc.example.com:50051" in msg  # what was discarded ...
    assert "localhost:8080" in msg  # ... and what is used instead
    assert "WebAssembly" in msg  # ... and why
    _assert_grpc_rides_rest(client)


def test_an_explicit_local_grpc_port_is_warned_about_but_the_default_is_not(emscripten) -> None:
    import weaviate

    with pytest.warns(UserWarning, match="Con006"):
        client = weaviate.use_async_with_local(port=8080, grpc_port=8081)
    _assert_grpc_rides_rest(client)
