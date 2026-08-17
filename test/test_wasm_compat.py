"""Unit tests for WASM/Pyodide-compatibility behavior that runs on CPython too.

Under Emscripten there are no subprocesses and no threads, and transport errors often
stringify to '' — these tests pin the guards and error-surfacing added for that
environment without needing a browser.
"""

import sys

import grpc
import pytest
from grpc.aio import AioRpcError, Metadata
from httpx import ConnectError, ConnectTimeout, PoolTimeout, ReadTimeout, WriteTimeout

from weaviate import WeaviateAsyncClient, WeaviateClient
from weaviate.config import ConnectionConfig
from weaviate.config import Timeout as TimeoutConfig
from weaviate.connect.base import ConnectionParams
from weaviate.connect.v4 import _ConnectionBase, _exc_detail
from weaviate.embedded import _EmbeddedBase
from weaviate.exceptions import (
    WeaviateClosedClientError,
    WeaviateConnectionError,
    WeaviateGRPCUnavailableError,
    WeaviateStartUpError,
    WeaviateTimeoutError,
)
from weaviate.util import _ServerVersion


def test_embedded_raises_explicit_error_under_emscripten(monkeypatch) -> None:
    # without the guard, the Emscripten socket emulation makes the port probe
    # "succeed" and embedded misreports that Weaviate is already listening
    monkeypatch.setattr(sys, "platform", "emscripten")
    with pytest.raises(WeaviateStartUpError, match="WebAssembly/Pyodide"):
        _EmbeddedBase.check_supported_platform()


def test_embedded_platform_check_passes_on_supported_platforms() -> None:
    assert sys.platform != "emscripten"
    _EmbeddedBase.check_supported_platform()  # must not raise on this dev platform


def test_sync_client_construction_raises_async_only_under_emscripten(monkeypatch) -> None:
    # without the guard the sync client constructs fine and the first REST call fails
    # with an opaque ConnectError; the clear async-only error must win, at construction
    monkeypatch.setattr(sys, "platform", "emscripten")
    with pytest.raises(WeaviateStartUpError, match="async client"):
        WeaviateClient(connection_params=ConnectionParams.from_url("http://localhost:8080", 50051))


def test_async_client_construction_allowed_under_emscripten(monkeypatch) -> None:
    # the async client is the supported one under WASM — the guard must not catch it
    monkeypatch.setattr(sys, "platform", "emscripten")
    client = WeaviateAsyncClient(
        connection_params=ConnectionParams.from_url("http://localhost:8080", 50051)
    )
    assert client is not None


def _handle_exceptions(e: Exception, error_msg: str = "") -> None:
    conn = object.__new__(_ConnectionBase)
    # keep the bare instance's __del__ quiet (it checks these for unclosed connections)
    conn._client = None
    conn._grpc_channel = None
    getattr(conn, "_ConnectionBase__handle_exceptions")(e, error_msg)  # noqa: B009


def test_httpx_closed_client_runtime_error_maps_to_closed_client() -> None:
    # the exact message httpx raises for a closed AsyncClient/Client
    with pytest.raises(WeaviateClosedClientError):
        _handle_exceptions(RuntimeError("Cannot send a request, as the client has been closed."))


def test_unrelated_runtime_error_is_not_rewritten_as_closed_client() -> None:
    # Emscripten's canonical thread failure must propagate as-is, not as a misleading
    # 'client is closed - run client.connect()'
    with pytest.raises(RuntimeError, match="can't start new thread"):
        _handle_exceptions(RuntimeError("can't start new thread"))


def test_connect_error_message_includes_exception_type() -> None:
    # str(httpx.ConnectError('')) == '' — the type name must still surface
    with pytest.raises(WeaviateConnectionError) as excinfo:
        _handle_exceptions(ConnectError(""))
    assert "ConnectError" in str(excinfo.value)


def test_read_timeout_message_includes_context_and_detail() -> None:
    with pytest.raises(WeaviateTimeoutError) as excinfo:
        _handle_exceptions(ReadTimeout(""), error_msg="Meta endpoint")
    assert "Meta endpoint" in str(excinfo.value)
    assert "ReadTimeout" in str(excinfo.value)


def test_exc_detail_formats_empty_and_nonempty_strs() -> None:
    assert _exc_detail(ValueError("boom")) == "ValueError: boom"
    assert _exc_detail(ConnectError("")) == "ConnectError('')"


@pytest.mark.parametrize(
    "error", [ConnectTimeout("Request timed out"), WriteTimeout(""), PoolTimeout("")]
)
def test_httpx_timeouts_map_into_the_weaviate_taxonomy(error: Exception) -> None:
    # ConnectTimeout/WriteTimeout/PoolTimeout subclass TimeoutException but neither
    # ConnectError nor ReadTimeout, so they used to escape as raw httpx errors. Pyodide
    # raises ConnectTimeout when the whole fetch promise exceeds the connect timeout.
    with pytest.raises(WeaviateTimeoutError) as excinfo:
        _handle_exceptions(error, error_msg="Meta endpoint")
    assert "Meta endpoint" in str(excinfo.value)
    assert type(error).__name__ in str(excinfo.value)


def _connection(prefix=None, *, insert: float = 90, query: float = 30) -> _ConnectionBase:
    conn = object.__new__(_ConnectionBase)
    conn._client = None
    conn._grpc_channel = None
    conn._weaviate_version = _ServerVersion.from_string("1.36.0")
    conn.timeout_config = TimeoutConfig(insert=insert, query=query)
    conn._ConnectionBase__connection_config = ConnectionConfig()  # type: ignore[attr-defined]
    conn._connection_params = ConnectionParams.from_url(
        "http://localhost:8080",
        grpc_port=8080 if prefix else 50051,
        grpc_path_prefix=prefix,
    )
    return conn


def _get_timeout(conn: _ConnectionBase, method: str, is_gql_query: bool = False):
    return getattr(conn, "_ConnectionBase__get_timeout")(method, is_gql_query)  # noqa: B009


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


def test_rest_timeouts_are_capped_at_five_seconds_on_native_platforms() -> None:
    assert sys.platform != "emscripten"
    conn = _connection()
    insert = _get_timeout(conn, "POST")
    assert insert.connect == 5.0 and insert.write == 5.0  # httpx defaults, unchanged
    assert insert.read == 90


def test_rest_connect_timeout_follows_the_request_timeout_under_emscripten(monkeypatch) -> None:
    # under Pyodide the connect timeout bounds the entire fetch promise, so a fixed 5s
    # silently caps every request at ~5s of wall clock
    monkeypatch.setattr(sys, "platform", "emscripten")
    conn = _connection()

    insert = _get_timeout(conn, "POST")
    assert insert.connect == 90 and insert.write == 90
    assert insert.read == 90

    query = _get_timeout(conn, "GET")
    assert query.connect == 30
    assert query.read == 30

    # a configured timeout below the httpx default must not make connecting stricter
    short = _get_timeout(_connection(insert=1, query=1), "POST")
    assert short.connect == 5.0
    assert short.read == 1
