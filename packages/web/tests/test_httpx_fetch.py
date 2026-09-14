"""Tests for the fetch-based httpx transport (``_httpx_fetch.py``).

Run inside Pyodide via ``ci/pyodide-e2e/units.mjs``. ``pyfetch`` is bound at import
time in ``_httpx_fetch``, so fakes patch that module attribute; ``from js import
AbortSignal`` is resolved per request, so a fake js module in ``sys.modules``
intercepts it even under real Pyodide.

The install-semantics tests at the bottom run against this interpreter's real
installation: importing ``weaviate_client_web`` bootstrapped the transport globally.
"""

import contextlib
import types
from typing import Any, Dict, List, Optional

import httpx
from harness import patched, raises, sys_module

import weaviate_client_web
import weaviate_client_web._httpx_fetch as _httpx_fetch
from weaviate_client_web._httpx_fetch import _MAX_ABORT_SIGNAL_MS, _abort_signal_ms


class FakeFetchResponse:
    def __init__(
        self, status: int = 200, headers: Optional[Any] = None, body: Optional[bytes] = b""
    ):
        self.status = status
        self.headers: Any = headers or {}
        self._body = body

    async def bytes(self) -> bytes:  # noqa: A003 - mirrors pyodide's FetchResponse API
        # a null JS body (HEAD, 204) resolves to an empty ArrayBuffer, i.e. b""
        return b"" if self._body is None else self._body


class FakePyfetch:
    def __init__(self, response: Optional[FakeFetchResponse] = None):
        self.response = response or FakeFetchResponse()
        self.calls: List[Dict[str, Any]] = []

    async def __call__(self, url: str, **kwargs: Any) -> FakeFetchResponse:
        self.calls.append({"url": url, **kwargs})
        return self.response


@contextlib.contextmanager
def fake_pyfetch():
    fetch = FakePyfetch()
    with patched(_httpx_fetch, "pyfetch", fetch):
        yield fetch


class _AbortSignalRecorder:
    def __init__(self):
        self.timeouts: List[int] = []

    def timeout(self, ms: int):
        self.timeouts.append(ms)
        return f"signal-{ms}"


@contextlib.contextmanager
def fake_abort_signal():
    recorder = _AbortSignalRecorder()
    js_mod = types.ModuleType("js")
    js_mod.AbortSignal = recorder  # type: ignore[attr-defined]
    with sys_module("js", js_mod):
        yield recorder


@contextlib.contextmanager
def missing_js_module():
    # sys.modules[name] = None makes ``import js`` raise ImportError — the closest
    # in-process stand-in for an environment without the js bridge.
    with sys_module("js", None):
        yield


async def _handle(request: httpx.Request) -> httpx.Response:
    # self is unused by the handler implementation; a bare transport instance suffices
    transport = httpx.AsyncHTTPTransport.__new__(httpx.AsyncHTTPTransport)
    response = await _httpx_fetch._fetch_handle_async_request(transport, request)
    await response.aread()  # httpx.AsyncClient reads non-streamed responses the same way
    return response


class _FetchTransport(httpx.AsyncBaseTransport):
    """Route an ``httpx.AsyncClient`` through the handler without touching global state."""

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return await _httpx_fetch._fetch_handle_async_request(self, request)  # type: ignore[arg-type]


async def _via_client(method: str, url: str, **kwargs: Any) -> httpx.Response:
    async with httpx.AsyncClient(transport=_FetchTransport()) as client:
        return await client.request(method, url, **kwargs)


async def test_basic_get_round_trip():
    with fake_pyfetch() as fetch:
        fetch.response = FakeFetchResponse(
            status=200, headers={"content-type": "application/json"}, body=b'{"version": "1.30.0"}'
        )
        response = await _handle(httpx.Request("GET", "http://h:8080/v1/meta"))

        assert response.status_code == 200
        assert response.json() == {"version": "1.30.0"}
        assert response.headers["content-type"] == "application/json"
        call = fetch.calls[0]
        assert call["url"] == "http://h:8080/v1/meta"
        assert call["method"] == "GET"


async def test_response_has_request_attached_for_raise_for_status():
    with fake_pyfetch() as fetch:
        fetch.response = FakeFetchResponse(status=404, body=b"")
        response = await _handle(httpx.Request("GET", "http://h:8080/v1/schema/Nope"))
        with raises(httpx.HTTPStatusError):
            response.raise_for_status()


async def test_head_response_without_body_yields_empty_content():
    # data.exists() / tenants.exists() are HEAD requests answered 204/404 with a null
    # body; the transport must hand httpx an empty response, not fail on the missing body
    for status in (204, 404):
        with fake_pyfetch() as fetch:
            fetch.response = FakeFetchResponse(status=status, body=None)
            response = await _handle(httpx.Request("HEAD", "http://h:8080/v1/objects/A/uuid"))
            assert response.status_code == status
            assert response.content == b""
            assert "body" not in fetch.calls[0]


async def test_delete_204_without_body_yields_empty_content():
    # data.delete_by_id() / reference_delete() are answered 204 with a null body
    with fake_pyfetch() as fetch:
        fetch.response = FakeFetchResponse(status=204, body=None)
        response = await _handle(httpx.Request("DELETE", "http://h:8080/v1/objects/A/uuid"))
        assert response.status_code == 204
        assert response.content == b""


async def test_body_less_response_through_async_client():
    # the full httpx.AsyncClient path (stream wrapping + read) on a body-less response
    with fake_pyfetch() as fetch:
        fetch.response = FakeFetchResponse(status=204, body=None)
        response = await _via_client("HEAD", "http://h:8080/v1/objects/A/uuid")
        assert response.status_code == 204
        assert response.content == b""


async def test_response_through_async_client_exposes_elapsed_and_content():
    # the batch-references path reads ``res.elapsed``, which httpx only sets after it
    # has read/closed a stream-backed response; a pre-loaded body never gets one
    payload = b'[{"result": {"status": "SUCCESS"}}]'
    with fake_pyfetch() as fetch:
        fetch.response = FakeFetchResponse(status=200, body=payload)
        response = await _via_client("POST", "http://h:8080/v1/batch/references", content=b"[]")
        assert response.content == payload
        assert response.json() == [{"result": {"status": "SUCCESS"}}]
        assert response.elapsed.total_seconds() >= 0


async def test_fetch_managed_request_headers_stripped():
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
    with fake_pyfetch() as fetch:
        await _handle(request)
        sent = fetch.calls[0]["headers"]
        assert sent["authorization"] == "Bearer k"
        assert sent["content-type"] == "application/json"
        for managed in (
            "host",
            "connection",
            "accept-encoding",
            "content-length",
            "transfer-encoding",
        ):
            assert managed not in sent, managed


async def test_get_without_body_omits_body_kwarg():
    # fetch rejects GET/HEAD requests that carry a body, so the kwarg must be absent
    with fake_pyfetch() as fetch:
        await _handle(httpx.Request("GET", "http://h:8080/v1/.well-known/ready"))
        assert "body" not in fetch.calls[0]


async def test_post_body_passed():
    with fake_pyfetch() as fetch:
        await _handle(httpx.Request("POST", "http://h:8080/v1/graphql", content=b'{"query": "x"}'))
        assert fetch.calls[0]["body"] == b'{"query": "x"}'


async def test_delete_with_body_passed():
    # the REST batch-delete path sends DELETE with a JSON body
    with fake_pyfetch() as fetch:
        await _handle(
            httpx.Request("DELETE", "http://h:8080/v1/batch/objects", content=b'{"match": {}}')
        )
        assert fetch.calls[0]["body"] == b'{"match": {}}'


async def test_query_string_preserved_in_url():
    with fake_pyfetch() as fetch:
        await _handle(httpx.Request("GET", "http://h:8080/v1/objects?class=A&limit=10&after=a%20b"))
        assert fetch.calls[0]["url"] == "http://h:8080/v1/objects?class=A&limit=10&after=a%20b"


async def test_content_encoding_stripped_from_response():
    # fetch hands back ALREADY-decompressed bytes; if the original content-encoding
    # header were passed through, httpx.Response would gunzip a second time and raise
    # DecodingError. content-length is stale for the same reason.
    with fake_pyfetch() as fetch:
        fetch.response = FakeFetchResponse(
            status=200,
            headers={"content-encoding": "gzip", "content-length": "23", "x-other": "kept"},
            body=b'{"version": "1.30.0"}',
        )
        response = await _handle(httpx.Request("GET", "http://h:8080/v1/meta"))
        assert response.json() == {"version": "1.30.0"}
        assert "content-encoding" not in response.headers
        assert response.headers["x-other"] == "kept"


async def test_unreadable_response_headers_tolerated():
    class BadHeaders:
        def keys(self):
            raise TypeError("header shape varies across Pyodide versions")

    with fake_pyfetch() as fetch:
        fetch.response = FakeFetchResponse(status=200, body=b"ok")
        fetch.response.headers = BadHeaders()
        response = await _handle(httpx.Request("GET", "http://h:8080/v1/meta"))
        assert response.status_code == 200
        assert response.content == b"ok"


def _request_with_timeout(timeouts: Dict[str, Optional[float]]) -> httpx.Request:
    request = httpx.Request("GET", "http://h:8080/v1/meta")
    request.extensions["timeout"] = timeouts
    return request


async def test_read_timeout_maps_to_abort_signal_ms():
    # mirrors what weaviate's AsyncClient puts in extensions: connect/read/write/pool
    with fake_pyfetch() as fetch, fake_abort_signal() as signals:
        await _handle(
            _request_with_timeout({"connect": 2.0, "read": 30.0, "write": 5.0, "pool": 9.0})
        )
        assert signals.timeouts == [30000]
        assert fetch.calls[0]["signal"] == "signal-30000"


async def test_read_none_means_no_deadline_even_with_pool_and_connect_set():
    # what the base client hands over for a non-finite request timeout: read=None with the
    # session pool timeout still set; falling back to pool/connect would abort a long
    # insert after 5 s
    with fake_pyfetch() as fetch, fake_abort_signal() as signals:
        await _handle(
            _request_with_timeout({"connect": None, "read": None, "write": None, "pool": 5})
        )
        await _handle(
            _request_with_timeout({"connect": 2.0, "read": None, "write": None, "pool": 9.0})
        )
        assert signals.timeouts == []
        assert all("signal" not in c for c in fetch.calls)


async def test_read_timeout_alone_sets_the_deadline():
    with fake_pyfetch() as fetch, fake_abort_signal() as signals:
        await _handle(_request_with_timeout({"connect": None, "read": 7, "write": None, "pool": 5}))
        assert signals.timeouts == [7000]
        assert fetch.calls[0]["signal"] == "signal-7000"


async def test_no_timeout_extension_sends_no_signal():
    with fake_pyfetch() as fetch, fake_abort_signal() as signals:
        await _handle(httpx.Request("GET", "http://h:8080/v1/meta"))
        assert signals.timeouts == []
        assert "signal" not in fetch.calls[0]


async def test_missing_js_module_degrades_to_no_signal():
    # without the js bridge the AbortSignal import fails; the request must still go out
    with fake_pyfetch() as fetch, missing_js_module():
        response = await _handle(
            _request_with_timeout({"connect": 2.0, "read": 30.0, "write": None, "pool": None})
        )
        assert response.status_code == 200
        assert "signal" not in fetch.calls[0]


async def test_zero_timeout_means_no_deadline():
    # an explicit read=0 must not fall through to the 5s connect timeout, nor become an
    # immediate AbortSignal.timeout(0)
    with fake_pyfetch() as fetch, fake_abort_signal() as signals:
        await _handle(
            _request_with_timeout({"connect": 5.0, "read": 0, "write": None, "pool": None})
        )
        assert signals.timeouts == []
        assert "signal" not in fetch.calls[0]


def test_abort_signal_ms_bounds():
    cases = [
        (None, None),
        (0, None),
        (-1, None),
        (float("inf"), None),
        (float("nan"), None),
        (0.0001, 1),  # rounds up: never an immediate AbortSignal.timeout(0)
        (30.0, 30_000),
        (1e8, _MAX_ABORT_SIGNAL_MS),
        (1e10, _MAX_ABORT_SIGNAL_MS),
        (1e308, _MAX_ABORT_SIGNAL_MS),  # finite, but *1000 overflows: capped, not an error
    ]
    for timeout, expected_ms in cases:
        assert _abort_signal_ms(timeout) == expected_ms, timeout


async def test_infinite_timeout_sends_no_signal():
    # an inf read deadline reaching the transport: no signal, not an OverflowError
    with fake_pyfetch() as fetch, fake_abort_signal() as signals:
        await _handle(
            _request_with_timeout({"connect": None, "read": float("inf"), "write": None, "pool": 5})
        )
        assert signals.timeouts == []
        assert "signal" not in fetch.calls[0]


async def test_huge_timeout_is_capped_to_int32_ms():
    # setTimeout delays above 2^31-1 ms overflow and fire at once, aborting the request
    with fake_pyfetch() as fetch, fake_abort_signal() as signals:
        await _handle(
            _request_with_timeout({"connect": None, "read": 1e10, "write": None, "pool": None})
        )
        assert signals.timeouts == [_MAX_ABORT_SIGNAL_MS]
        assert fetch.calls[0]["signal"] == f"signal-{_MAX_ABORT_SIGNAL_MS}"


class RaisingPyfetch:
    def __init__(self, exc: BaseException):
        self.exc = exc

    async def __call__(self, url: str, **kwargs: Any):
        raise self.exc


@contextlib.contextmanager
def raising_pyfetch(exc: BaseException):
    with patched(_httpx_fetch, "pyfetch", RaisingPyfetch(exc)):
        yield


async def test_fetch_failure_maps_to_httpx_connect_error():
    # pyodide surfaces JS fetch rejections as OSError; the base client can only classify
    # httpx exceptions (WeaviateConnectionError etc.), so the shim must translate
    with raising_pyfetch(OSError("TypeError: Failed to fetch")):
        with raises(httpx.ConnectError, contains="Failed to fetch") as excinfo:
            await _handle(httpx.Request("GET", "http://h:8080/v1/meta"))
        assert isinstance(excinfo.value.__cause__, OSError)


async def test_fetch_abort_with_deadline_maps_to_read_timeout():
    # AbortSignal.timeout firing surfaces as an OSError subclass mentioning the abort;
    # with a deadline set this must classify as a timeout, not a connection error
    with raising_pyfetch(OSError("AbortError: signal timed out")), fake_abort_signal():
        with raises(httpx.ReadTimeout, contains="signal timed out"):
            await _handle(
                _request_with_timeout({"connect": None, "read": 0.5, "write": None, "pool": None})
            )


async def test_fetch_failure_with_deadline_but_no_timeout_message_stays_connect_error():
    # nearly every weaviate request sets a read deadline; a plain network failure on
    # such a request must remain a connection error, not become a timeout
    with raising_pyfetch(OSError("TypeError: Failed to fetch")), fake_abort_signal():
        with raises(httpx.ConnectError, contains="Failed to fetch"):
            await _handle(
                _request_with_timeout({"connect": None, "read": 30.0, "write": None, "pool": None})
            )


async def test_fetch_abort_without_deadline_stays_connect_error():
    # the same message without a deadline set (no js bridge -> no signal) is not OUR
    # timeout, so it must stay a connection error
    with raising_pyfetch(OSError("AbortError: signal timed out")), missing_js_module():
        with raises(httpx.ConnectError):
            await _handle(
                _request_with_timeout({"connect": None, "read": 0.5, "write": None, "pool": None})
            )


async def test_empty_oserror_str_keeps_repr_detail():
    with raising_pyfetch(OSError()):
        with raises(httpx.ConnectError) as excinfo:
            await _handle(httpx.Request("GET", "http://h:8080/v1/meta"))
        assert "OSError" in str(excinfo.value)


async def test_crlf_in_header_value_rejected():
    # httpx.Request accepts CR/LF in header values and relies on h11 to reject them at
    # send time; this transport bypasses h11 and must keep that defence
    request = httpx.Request(
        "GET", "http://h:8080/v1/meta", headers={"x-key": "val\r\nx-injected: evil"}
    )
    with fake_pyfetch() as fetch:
        with raises(httpx.LocalProtocolError):
            await _handle(request)
        assert fetch.calls == []


# ---------------------------------------------------------------------------
# install semantics, against this interpreter's real installation
# ---------------------------------------------------------------------------


def test_bootstrap_installed_fetch_transport():
    # This interpreter imported weaviate_client_web at the top of this file, so the real
    # bootstrap ran — even though Pyodide's bundled httpx carries its own jsfetch
    # transport, the package's transport must be the active one.
    assert weaviate_client_web.is_fetch_transport_installed()
    assert (
        getattr(httpx.AsyncHTTPTransport.handle_async_request, "__weaviate_fetch_shim__", False)
        is True
    )


def test_install_fetch_transport_is_idempotent():
    patched_method = httpx.AsyncHTTPTransport.handle_async_request
    weaviate_client_web.install_fetch_transport()
    assert httpx.AsyncHTTPTransport.handle_async_request is patched_method


def test_sync_transport_left_untouched():
    assert not getattr(httpx.HTTPTransport.handle_request, "__weaviate_fetch_shim__", False)


def test_uninstall_restores_original_transport():
    patched_method = httpx.AsyncHTTPTransport.handle_async_request
    try:
        weaviate_client_web.uninstall_fetch_transport()
        assert not weaviate_client_web.is_fetch_transport_installed()
        assert httpx.AsyncHTTPTransport.handle_async_request is not patched_method
        assert not getattr(
            httpx.AsyncHTTPTransport.handle_async_request, "__weaviate_fetch_shim__", False
        )
        weaviate_client_web.uninstall_fetch_transport()  # no-op when not installed
    finally:
        weaviate_client_web.install_fetch_transport()
    assert weaviate_client_web.is_fetch_transport_installed()
    assert (
        getattr(httpx.AsyncHTTPTransport.handle_async_request, "__weaviate_fetch_shim__", False)
        is True
    )


async def test_installed_transport_routes_async_client_through_pyfetch():
    # the globally installed transport (no custom transport argument) must reach pyfetch
    with fake_pyfetch() as fetch:
        fetch.response = FakeFetchResponse(
            status=200, headers={"content-type": "application/json"}, body=b'{"ok": true}'
        )
        async with httpx.AsyncClient() as client:
            response = await client.get("http://h:8080/v1/meta")
        assert response.status_code == 200
        assert response.json() == {"ok": True}
        assert fetch.calls and fetch.calls[0]["url"] == "http://h:8080/v1/meta"
