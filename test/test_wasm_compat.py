"""Unit tests for WASM/Pyodide-compatibility behavior that runs on CPython too.

Under Emscripten there are no subprocesses and no threads, and transport errors often
stringify to '' — these tests pin the guards and error-surfacing added for that
environment without needing a browser.
"""

import sys

import pytest
from httpx import ConnectError, ReadTimeout

from weaviate.connect.v4 import _ConnectionBase, _exc_detail
from weaviate.embedded import _EmbeddedBase
from weaviate.exceptions import (
    WeaviateClosedClientError,
    WeaviateConnectionError,
    WeaviateStartUpError,
    WeaviateTimeoutError,
)


def test_embedded_raises_explicit_error_under_emscripten(monkeypatch) -> None:
    # without the guard, the Emscripten socket emulation makes the port probe
    # "succeed" and embedded misreports that Weaviate is already listening
    monkeypatch.setattr(sys, "platform", "emscripten")
    with pytest.raises(WeaviateStartUpError, match="WebAssembly/Pyodide"):
        _EmbeddedBase.check_supported_platform()


def test_embedded_platform_check_passes_on_supported_platforms() -> None:
    assert sys.platform != "emscripten"
    _EmbeddedBase.check_supported_platform()  # must not raise on this dev platform


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
