"""Tests for the fetch-based httpx transport (_httpx_fetch.py).

In-process tests call ``_fetch_handle_async_request`` directly with a fake
``pyodide.http`` module injected into ``sys.modules`` — no global monkeypatch of
``httpx.AsyncHTTPTransport`` is needed, so the real httpx in the dev environment is left
untouched. Install semantics (which DO patch the class globally) run in fresh
subprocesses, mirroring test_shim_install.py.
"""

import asyncio
import pathlib
import subprocess
import sys
import textwrap
import types
from typing import Any, Dict, List, Optional

import httpx
import pytest

from weaviate_grpc_web._httpx_fetch import _fetch_handle_async_request

_SRC = str(pathlib.Path(__file__).resolve().parents[1] / "src")


class FakeFetchResponse:
    def __init__(self, status: int = 200, headers: Optional[Any] = None, body: bytes = b""):
        self.status = status
        self.headers: Any = headers or {}
        self._body = body

    async def bytes(self) -> bytes:  # noqa: A003 - mirrors pyodide's FetchResponse API
        return self._body


class FakePyfetch:
    def __init__(self, response: Optional[FakeFetchResponse] = None):
        self.response = response or FakeFetchResponse()
        self.calls: List[Dict[str, Any]] = []

    async def __call__(self, url: str, **kwargs: Any) -> FakeFetchResponse:
        self.calls.append({"url": url, **kwargs})
        return self.response


@pytest.fixture
def fake_pyfetch(monkeypatch) -> FakePyfetch:
    fetch = FakePyfetch()
    pyodide_mod = types.ModuleType("pyodide")
    http_mod = types.ModuleType("pyodide.http")
    http_mod.pyfetch = fetch  # type: ignore[attr-defined]
    pyodide_mod.http = http_mod  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pyodide", pyodide_mod)
    monkeypatch.setitem(sys.modules, "pyodide.http", http_mod)
    return fetch


def _handle(request: httpx.Request) -> httpx.Response:
    # self is unused by the handler implementation; a bare transport instance suffices
    transport = httpx.AsyncHTTPTransport.__new__(httpx.AsyncHTTPTransport)
    return asyncio.run(_fetch_handle_async_request(transport, request))


def test_basic_get_round_trip(fake_pyfetch):
    fake_pyfetch.response = FakeFetchResponse(
        status=200, headers={"content-type": "application/json"}, body=b'{"version": "1.30.0"}'
    )
    response = _handle(httpx.Request("GET", "http://h:8080/v1/meta"))

    assert response.status_code == 200
    assert response.json() == {"version": "1.30.0"}
    assert response.headers["content-type"] == "application/json"
    call = fake_pyfetch.calls[0]
    assert call["url"] == "http://h:8080/v1/meta"
    assert call["method"] == "GET"


def test_response_has_request_attached_for_raise_for_status(fake_pyfetch):
    fake_pyfetch.response = FakeFetchResponse(status=404, body=b"")
    response = _handle(httpx.Request("GET", "http://h:8080/v1/schema/Nope"))
    with pytest.raises(httpx.HTTPStatusError):
        response.raise_for_status()


def test_fetch_managed_request_headers_stripped(fake_pyfetch):
    request = httpx.Request(
        "POST",
        "http://h:8080/v1/objects",
        headers={
            "authorization": "Bearer k",
            "content-type": "application/json",
            "host": "h:8080",
            "connection": "keep-alive",
            "accept-encoding": "gzip",
            "transfer-encoding": "chunked",
        },
        content=b"{}",
    )
    _handle(request)
    sent = fake_pyfetch.calls[0]["headers"]
    assert sent["authorization"] == "Bearer k"
    assert sent["content-type"] == "application/json"
    for managed in ("host", "connection", "accept-encoding", "content-length", "transfer-encoding"):
        assert managed not in sent


def test_get_without_body_omits_body_kwarg(fake_pyfetch):
    # fetch rejects GET/HEAD requests that carry a body, so the kwarg must be absent
    _handle(httpx.Request("GET", "http://h:8080/v1/.well-known/ready"))
    assert "body" not in fake_pyfetch.calls[0]


def test_post_body_passed(fake_pyfetch):
    _handle(httpx.Request("POST", "http://h:8080/v1/graphql", content=b'{"query": "x"}'))
    assert fake_pyfetch.calls[0]["body"] == b'{"query": "x"}'


def test_delete_with_body_passed(fake_pyfetch):
    # the REST batch-delete path sends DELETE with a JSON body
    _handle(httpx.Request("DELETE", "http://h:8080/v1/batch/objects", content=b'{"match": {}}'))
    assert fake_pyfetch.calls[0]["body"] == b'{"match": {}}'


def test_query_string_preserved_in_url(fake_pyfetch):
    _handle(httpx.Request("GET", "http://h:8080/v1/objects?class=A&limit=10&after=a%20b"))
    assert fake_pyfetch.calls[0]["url"] == "http://h:8080/v1/objects?class=A&limit=10&after=a%20b"


def test_content_encoding_stripped_from_response(fake_pyfetch):
    # fetch hands back ALREADY-decompressed bytes; if the original content-encoding
    # header were passed through, httpx.Response would gunzip a second time and raise
    # DecodingError. content-length is stale for the same reason.
    fake_pyfetch.response = FakeFetchResponse(
        status=200,
        headers={"content-encoding": "gzip", "content-length": "23", "x-other": "kept"},
        body=b'{"version": "1.30.0"}',
    )
    response = _handle(httpx.Request("GET", "http://h:8080/v1/meta"))
    assert response.json() == {"version": "1.30.0"}
    assert "content-encoding" not in response.headers
    assert response.headers["x-other"] == "kept"


def test_unreadable_response_headers_tolerated(fake_pyfetch):
    class BadHeaders:
        def keys(self):
            raise TypeError("header shape varies across Pyodide versions")

    fake_pyfetch.response = FakeFetchResponse(status=200, body=b"ok")
    fake_pyfetch.response.headers = BadHeaders()
    response = _handle(httpx.Request("GET", "http://h:8080/v1/meta"))
    assert response.status_code == 200
    assert response.content == b"ok"


class _AbortSignalRecorder:
    def __init__(self):
        self.timeouts: List[int] = []

    def timeout(self, ms: int):
        self.timeouts.append(ms)
        return f"signal-{ms}"


@pytest.fixture
def fake_abort_signal(monkeypatch) -> _AbortSignalRecorder:
    recorder = _AbortSignalRecorder()
    js_mod = types.ModuleType("js")
    js_mod.AbortSignal = recorder  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "js", js_mod)
    return recorder


def _request_with_timeout(timeouts: Dict[str, Optional[float]]) -> httpx.Request:
    request = httpx.Request("GET", "http://h:8080/v1/meta")
    request.extensions["timeout"] = timeouts
    return request


def test_read_timeout_maps_to_abort_signal_ms(fake_pyfetch, fake_abort_signal):
    # mirrors what weaviate's AsyncClient puts in extensions: connect/read/write/pool
    _handle(_request_with_timeout({"connect": 2.0, "read": 30.0, "write": 5.0, "pool": 9.0}))
    assert fake_abort_signal.timeouts == [30000]
    assert fake_pyfetch.calls[0]["signal"] == "signal-30000"


def test_timeout_falls_back_to_connect_then_pool(fake_pyfetch, fake_abort_signal):
    _handle(_request_with_timeout({"connect": 2.0, "read": None, "write": None, "pool": 9.0}))
    _handle(_request_with_timeout({"connect": None, "read": None, "write": None, "pool": 9.0}))
    assert fake_abort_signal.timeouts == [2000, 9000]
    assert [c["signal"] for c in fake_pyfetch.calls] == ["signal-2000", "signal-9000"]


def test_no_timeout_extension_sends_no_signal(fake_pyfetch, fake_abort_signal):
    _handle(httpx.Request("GET", "http://h:8080/v1/meta"))
    assert fake_abort_signal.timeouts == []
    assert "signal" not in fake_pyfetch.calls[0]


def test_missing_js_module_degrades_to_no_signal(fake_pyfetch):
    # off-browser (no js module) the AbortSignal import fails; the request must still go out
    assert "js" not in sys.modules
    response = _handle(
        _request_with_timeout({"connect": 2.0, "read": 30.0, "write": None, "pool": None})
    )
    assert response.status_code == 200
    assert "signal" not in fake_pyfetch.calls[0]


def test_zero_timeout_means_no_deadline(fake_pyfetch, fake_abort_signal):
    # an explicit read=0 must not fall through to the 5s connect timeout, nor become an
    # immediate AbortSignal.timeout(0)
    _handle(_request_with_timeout({"connect": 5.0, "read": 0, "write": None, "pool": None}))
    assert fake_abort_signal.timeouts == []
    assert "signal" not in fake_pyfetch.calls[0]


class RaisingPyfetch:
    def __init__(self, exc: BaseException):
        self.exc = exc

    async def __call__(self, url: str, **kwargs: Any):
        raise self.exc


def _install_raising_pyfetch(monkeypatch, exc: BaseException) -> None:
    pyodide_mod = types.ModuleType("pyodide")
    http_mod = types.ModuleType("pyodide.http")
    http_mod.pyfetch = RaisingPyfetch(exc)  # type: ignore[attr-defined]
    pyodide_mod.http = http_mod  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pyodide", pyodide_mod)
    monkeypatch.setitem(sys.modules, "pyodide.http", http_mod)


def test_fetch_failure_maps_to_httpx_connect_error(monkeypatch):
    # pyodide surfaces JS fetch rejections as OSError; the base client can only classify
    # httpx exceptions (WeaviateConnectionError etc.), so the shim must translate
    _install_raising_pyfetch(monkeypatch, OSError("TypeError: Failed to fetch"))
    with pytest.raises(httpx.ConnectError, match="Failed to fetch") as excinfo:
        _handle(httpx.Request("GET", "http://h:8080/v1/meta"))
    assert isinstance(excinfo.value.__cause__, OSError)


def test_fetch_abort_with_deadline_maps_to_read_timeout(monkeypatch, fake_abort_signal):
    # AbortSignal.timeout firing surfaces as an OSError subclass mentioning the abort;
    # with a deadline set this must classify as a timeout, not a connection error
    _install_raising_pyfetch(monkeypatch, OSError("AbortError: signal timed out"))
    with pytest.raises(httpx.ReadTimeout, match="signal timed out"):
        _handle(_request_with_timeout({"connect": None, "read": 0.5, "write": None, "pool": None}))


def test_fetch_failure_with_deadline_but_no_timeout_message_stays_connect_error(
    monkeypatch, fake_abort_signal
):
    # nearly every weaviate request sets a read deadline; a plain network failure on
    # such a request must remain a connection error, not become a timeout
    _install_raising_pyfetch(monkeypatch, OSError("TypeError: Failed to fetch"))
    with pytest.raises(httpx.ConnectError, match="Failed to fetch"):
        _handle(_request_with_timeout({"connect": None, "read": 30.0, "write": None, "pool": None}))


def test_fetch_abort_without_deadline_stays_connect_error(monkeypatch):
    # the same message without a deadline set (no js module -> no signal) is not OUR
    # timeout, so it must stay a connection error
    _install_raising_pyfetch(monkeypatch, OSError("AbortError: signal timed out"))
    assert "js" not in sys.modules
    with pytest.raises(httpx.ConnectError):
        _handle(_request_with_timeout({"connect": None, "read": 0.5, "write": None, "pool": None}))


def test_empty_oserror_str_keeps_repr_detail(monkeypatch):
    _install_raising_pyfetch(monkeypatch, OSError())
    with pytest.raises(httpx.ConnectError) as excinfo:
        _handle(httpx.Request("GET", "http://h:8080/v1/meta"))
    assert "OSError" in str(excinfo.value)


def test_crlf_in_header_value_rejected(fake_pyfetch):
    # httpx.Request accepts CR/LF in header values and relies on h11 to reject them at
    # send time; this transport bypasses h11 and must keep that defence
    request = httpx.Request(
        "GET", "http://h:8080/v1/meta", headers={"x-key": "val\r\nx-injected: evil"}
    )
    with pytest.raises(httpx.LocalProtocolError):
        _handle(request)
    assert fake_pyfetch.calls == []


def test_platform_jsfetch_detection(monkeypatch):
    import importlib.machinery

    from weaviate_grpc_web._httpx_fetch import _platform_httpx_has_fetch_support

    # the dev environment runs PyPI httpx (httpcore-based): no jsfetch transport
    assert _platform_httpx_has_fetch_support() is False

    fake = types.ModuleType("httpx._transports.jsfetch")
    fake.__spec__ = importlib.machinery.ModuleSpec("httpx._transports.jsfetch", loader=None)
    monkeypatch.setitem(sys.modules, "httpx._transports.jsfetch", fake)
    assert _platform_httpx_has_fetch_support() is True


# ---------------------------------------------------------------------------
# Install semantics: these patch httpx.AsyncHTTPTransport globally, so each
# scenario runs in a fresh subprocess (same pattern as test_shim_install.py).
# ---------------------------------------------------------------------------

_FAKE_PYODIDE_PRELUDE = """
import sys, types

class _FakeResponse:
    status = 200
    headers = {"content-type": "application/json"}
    async def bytes(self):
        return b'{"ok": true}'

CALLS = []
async def pyfetch(url, **kwargs):
    CALLS.append((url, kwargs))
    return _FakeResponse()

_pyodide = types.ModuleType("pyodide")
_http = types.ModuleType("pyodide.http")
_http.pyfetch = pyfetch
_pyodide.http = _http
sys.modules["pyodide"] = _pyodide
sys.modules["pyodide.http"] = _http
"""


def _run(body: str, prelude: str = "") -> subprocess.CompletedProcess:
    script = f"import sys\nsys.path.insert(0, {_SRC!r})\n" + prelude + textwrap.dedent(body)
    return subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)


def test_force_install_routes_async_client_through_pyfetch():
    result = _run(
        prelude=_FAKE_PYODIDE_PRELUDE,
        body="""
        import asyncio, httpx
        from weaviate_grpc_web import install_fetch_transport, is_fetch_transport_installed

        install_fetch_transport(force=True)
        assert is_fetch_transport_installed()

        async def main():
            async with httpx.AsyncClient() as client:
                return await client.get("http://h:8080/v1/meta")

        resp = asyncio.run(main())
        assert resp.status_code == 200, resp.status_code
        assert resp.json() == {"ok": True}
        assert CALLS and CALLS[0][0] == "http://h:8080/v1/meta"
        print("OK")
        """,
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_install_without_force_is_noop_off_emscripten():
    result = _run(
        """
        import sys
        assert sys.platform != "emscripten"
        import httpx
        before = httpx.AsyncHTTPTransport.handle_async_request
        from weaviate_grpc_web import install_fetch_transport, is_fetch_transport_installed
        install_fetch_transport()
        assert not is_fetch_transport_installed()
        assert httpx.AsyncHTTPTransport.handle_async_request is before
        print("OK")
        """
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_force_install_is_idempotent():
    result = _run(
        prelude=_FAKE_PYODIDE_PRELUDE,
        body="""
        import httpx
        from weaviate_grpc_web import install_fetch_transport
        install_fetch_transport(force=True)
        patched = httpx.AsyncHTTPTransport.handle_async_request
        install_fetch_transport(force=True)
        assert httpx.AsyncHTTPTransport.handle_async_request is patched
        print("OK")
        """,
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_sync_transport_left_untouched():
    result = _run(
        prelude=_FAKE_PYODIDE_PRELUDE,
        body="""
        import httpx
        sync_before = httpx.HTTPTransport.handle_request
        from weaviate_grpc_web import install_fetch_transport
        install_fetch_transport(force=True)
        assert httpx.HTTPTransport.handle_request is sync_before
        print("OK")
        """,
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_uninstall_restores_original_transport():
    result = _run(
        prelude=_FAKE_PYODIDE_PRELUDE,
        body="""
        import httpx
        before = httpx.AsyncHTTPTransport.handle_async_request
        from weaviate_grpc_web import (
            install_fetch_transport,
            is_fetch_transport_installed,
            uninstall_fetch_transport,
        )
        uninstall_fetch_transport()  # no-op when not installed
        install_fetch_transport(force=True)
        assert is_fetch_transport_installed()
        assert httpx.AsyncHTTPTransport.handle_async_request is not before
        uninstall_fetch_transport()
        assert not is_fetch_transport_installed()
        assert httpx.AsyncHTTPTransport.handle_async_request is before
        print("OK")
        """,
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_patched_method_carries_sentinel():
    result = _run(
        prelude=_FAKE_PYODIDE_PRELUDE,
        body="""
        import httpx
        from weaviate_grpc_web import install_fetch_transport
        assert not getattr(
            httpx.AsyncHTTPTransport.handle_async_request, "__weaviate_fetch_shim__", False
        )
        install_fetch_transport(force=True)
        assert getattr(
            httpx.AsyncHTTPTransport.handle_async_request, "__weaviate_fetch_shim__", False
        ) is True
        print("OK")
        """,
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_force_install_without_pyodide_fails_fast():
    # without a pyodide module the install must raise immediately, not let every later
    # request die with a lazy ModuleNotFoundError
    result = _run(
        """
        import httpx
        before = httpx.AsyncHTTPTransport.handle_async_request
        from weaviate_grpc_web import install_fetch_transport, is_fetch_transport_installed
        try:
            install_fetch_transport(force=True)
        except ModuleNotFoundError:
            assert not is_fetch_transport_installed()
            assert httpx.AsyncHTTPTransport.handle_async_request is before
            print("OK")
        else:
            raise AssertionError("expected install to fail fast without pyodide")
        """
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout


def test_emscripten_with_platform_jsfetch_skips_install():
    # on Pyodide's distributed httpx (jsfetch transport built in), the shim must NOT
    # overwrite the platform implementation
    result = _run(
        """
        import importlib.machinery, sys, types

        sys.platform = "emscripten"
        fake = types.ModuleType("httpx._transports.jsfetch")
        fake.__spec__ = importlib.machinery.ModuleSpec(
            "httpx._transports.jsfetch", loader=None
        )
        sys.modules["httpx._transports.jsfetch"] = fake

        import httpx
        before = httpx.AsyncHTTPTransport.handle_async_request
        from weaviate_grpc_web import install_fetch_transport, is_fetch_transport_installed
        install_fetch_transport()  # no force: platform transport must win
        assert not is_fetch_transport_installed()
        assert httpx.AsyncHTTPTransport.handle_async_request is before
        print("OK")
        """
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout
