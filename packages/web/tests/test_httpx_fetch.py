"""Tests for _httpx_fetch. Fakes patch _httpx_fetch.pyfetch and sys.modules["js"].

The install tests at the bottom use the real bootstrap.
"""

import sys
import types
from typing import Any, Dict, List, Optional

import httpx
import pytest

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


@pytest.fixture
def fake_pyfetch(monkeypatch) -> FakePyfetch:
    fetch = FakePyfetch()
    monkeypatch.setattr(_httpx_fetch, "pyfetch", fetch)
    return fetch


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


@pytest.fixture
def missing_js(monkeypatch):
    # sys.modules["js"] = None makes ``import js`` raise ImportError — the closest
    # in-process stand-in for an environment without the js bridge
    monkeypatch.setitem(sys.modules, "js", None)


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


async def test_basic_get_round_trip(fake_pyfetch):
    fake_pyfetch.response = FakeFetchResponse(
        status=200, headers={"content-type": "application/json"}, body=b'{"version": "1.30.0"}'
    )
    response = await _handle(httpx.Request("GET", "http://h:8080/v1/meta"))

    assert response.status_code == 200
    assert response.json() == {"version": "1.30.0"}
    assert response.headers["content-type"] == "application/json"
    call = fake_pyfetch.calls[0]
    assert call["url"] == "http://h:8080/v1/meta"
    assert call["method"] == "GET"


async def test_response_has_request_attached_for_raise_for_status(fake_pyfetch):
    fake_pyfetch.response = FakeFetchResponse(status=404, body=b"")
    response = await _handle(httpx.Request("GET", "http://h:8080/v1/schema/Nope"))
    with pytest.raises(httpx.HTTPStatusError):
        response.raise_for_status()


@pytest.mark.parametrize("status", [204, 404])
async def test_head_response_without_body_yields_empty_content(fake_pyfetch, status):
    # data.exists() / tenants.exists() are HEAD requests answered 204/404 with a null
    # body; the transport must hand httpx an empty response, not fail on the missing body
    fake_pyfetch.response = FakeFetchResponse(status=status, body=None)
    response = await _handle(httpx.Request("HEAD", "http://h:8080/v1/objects/A/uuid"))
    assert response.status_code == status
    assert response.content == b""
    assert "body" not in fake_pyfetch.calls[0]


async def test_delete_204_without_body_yields_empty_content(fake_pyfetch):
    # data.delete_by_id() / reference_delete() are answered 204 with a null body
    fake_pyfetch.response = FakeFetchResponse(status=204, body=None)
    response = await _handle(httpx.Request("DELETE", "http://h:8080/v1/objects/A/uuid"))
    assert response.status_code == 204
    assert response.content == b""


async def test_body_less_response_through_async_client(fake_pyfetch):
    # the full httpx.AsyncClient path (stream wrapping + read) on a body-less response
    fake_pyfetch.response = FakeFetchResponse(status=204, body=None)
    response = await _via_client("HEAD", "http://h:8080/v1/objects/A/uuid")
    assert response.status_code == 204
    assert response.content == b""


async def test_response_through_async_client_exposes_elapsed_and_content(fake_pyfetch):
    # the batch-references path reads ``res.elapsed``, which httpx only sets after it
    # has read/closed a stream-backed response; a pre-loaded body never gets one
    payload = b'[{"result": {"status": "SUCCESS"}}]'
    fake_pyfetch.response = FakeFetchResponse(status=200, body=payload)
    response = await _via_client("POST", "http://h:8080/v1/batch/references", content=b"[]")
    assert response.content == payload
    assert response.json() == [{"result": {"status": "SUCCESS"}}]
    assert response.elapsed.total_seconds() >= 0


async def test_fetch_managed_request_headers_stripped(fake_pyfetch):
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
    await _handle(request)
    sent = fake_pyfetch.calls[0]["headers"]
    assert sent["authorization"] == "Bearer k"
    assert sent["content-type"] == "application/json"
    for managed in ("host", "connection", "accept-encoding", "content-length", "transfer-encoding"):
        assert managed not in sent


async def test_get_without_body_omits_body_kwarg(fake_pyfetch):
    # fetch rejects GET/HEAD requests that carry a body, so the kwarg must be absent
    await _handle(httpx.Request("GET", "http://h:8080/v1/.well-known/ready"))
    assert "body" not in fake_pyfetch.calls[0]


async def test_post_body_passed(fake_pyfetch):
    await _handle(httpx.Request("POST", "http://h:8080/v1/graphql", content=b'{"query": "x"}'))
    assert fake_pyfetch.calls[0]["body"] == b'{"query": "x"}'


async def test_delete_with_body_passed(fake_pyfetch):
    # the REST batch-delete path sends DELETE with a JSON body
    await _handle(
        httpx.Request("DELETE", "http://h:8080/v1/batch/objects", content=b'{"match": {}}')
    )
    assert fake_pyfetch.calls[0]["body"] == b'{"match": {}}'


async def test_query_string_preserved_in_url(fake_pyfetch):
    await _handle(httpx.Request("GET", "http://h:8080/v1/objects?class=A&limit=10&after=a%20b"))
    assert fake_pyfetch.calls[0]["url"] == "http://h:8080/v1/objects?class=A&limit=10&after=a%20b"


async def test_content_encoding_stripped_from_response(fake_pyfetch):
    # fetch returns decoded bytes; passing content-encoding through would decode twice
    fake_pyfetch.response = FakeFetchResponse(
        status=200,
        headers={"content-encoding": "gzip", "content-length": "23", "x-other": "kept"},
        body=b'{"version": "1.30.0"}',
    )
    response = await _handle(httpx.Request("GET", "http://h:8080/v1/meta"))
    assert response.json() == {"version": "1.30.0"}
    assert "content-encoding" not in response.headers
    assert response.headers["x-other"] == "kept"


async def test_unreadable_response_headers_tolerated(fake_pyfetch):
    class BadHeaders:
        def keys(self):
            raise TypeError("header shape varies across Pyodide versions")

    fake_pyfetch.response = FakeFetchResponse(status=200, body=b"ok")
    fake_pyfetch.response.headers = BadHeaders()
    response = await _handle(httpx.Request("GET", "http://h:8080/v1/meta"))
    assert response.status_code == 200
    assert response.content == b"ok"


def _request_with_timeout(timeouts: Dict[str, Optional[float]]) -> httpx.Request:
    request = httpx.Request("GET", "http://h:8080/v1/meta")
    request.extensions["timeout"] = timeouts
    return request


async def test_read_timeout_maps_to_abort_signal_ms(fake_pyfetch, fake_abort_signal):
    # mirrors what weaviate's AsyncClient puts in extensions: connect/read/write/pool
    await _handle(_request_with_timeout({"connect": 2.0, "read": 30.0, "write": 5.0, "pool": 9.0}))
    assert fake_abort_signal.timeouts == [30000]
    assert fake_pyfetch.calls[0]["signal"] == "signal-30000"


async def test_read_none_means_no_deadline_even_with_pool_and_connect_set(
    fake_pyfetch, fake_abort_signal
):
    # a non-finite timeout arrives as read=None with pool set; pool must not become the deadline
    await _handle(_request_with_timeout({"connect": None, "read": None, "write": None, "pool": 5}))
    await _handle(_request_with_timeout({"connect": 2.0, "read": None, "write": None, "pool": 9.0}))
    assert fake_abort_signal.timeouts == []
    assert all("signal" not in c for c in fake_pyfetch.calls)


async def test_read_timeout_alone_sets_the_deadline(fake_pyfetch, fake_abort_signal):
    await _handle(_request_with_timeout({"connect": None, "read": 7, "write": None, "pool": 5}))
    assert fake_abort_signal.timeouts == [7000]
    assert fake_pyfetch.calls[0]["signal"] == "signal-7000"


async def test_no_timeout_extension_sends_no_signal(fake_pyfetch, fake_abort_signal):
    await _handle(httpx.Request("GET", "http://h:8080/v1/meta"))
    assert fake_abort_signal.timeouts == []
    assert "signal" not in fake_pyfetch.calls[0]


async def test_missing_js_module_degrades_to_no_signal(fake_pyfetch, missing_js):
    # without the js bridge the AbortSignal import fails; the request must still go out
    response = await _handle(
        _request_with_timeout({"connect": 2.0, "read": 30.0, "write": None, "pool": None})
    )
    assert response.status_code == 200
    assert "signal" not in fake_pyfetch.calls[0]


async def test_zero_timeout_is_an_immediate_deadline(fake_pyfetch, fake_abort_signal):
    # read=0 is an immediate deadline, as in httpx; connect is ignored
    await _handle(_request_with_timeout({"connect": 5.0, "read": 0, "write": None, "pool": None}))
    assert fake_abort_signal.timeouts == [0]
    assert fake_pyfetch.calls[0]["signal"] == "signal-0"


@pytest.mark.parametrize(
    "timeout,expected_ms",
    [
        (None, None),
        (0, 0),  # immediate deadline, matching native httpx read=0
        (-1, None),
        (float("inf"), None),
        (float("nan"), None),
        (0.0001, 1),  # rounds up: never an immediate AbortSignal.timeout(0)
        (30.0, 30_000),
        (1e8, _MAX_ABORT_SIGNAL_MS),
        (1e10, _MAX_ABORT_SIGNAL_MS),
        (1e308, _MAX_ABORT_SIGNAL_MS),  # finite, but *1000 overflows: capped, not an error
    ],
)
def test_abort_signal_ms_bounds(timeout, expected_ms):
    assert _abort_signal_ms(timeout) == expected_ms


async def test_infinite_timeout_sends_no_signal(fake_pyfetch, fake_abort_signal):
    # an inf read deadline reaching the transport: no signal, not an OverflowError
    await _handle(
        _request_with_timeout({"connect": None, "read": float("inf"), "write": None, "pool": 5})
    )
    assert fake_abort_signal.timeouts == []
    assert "signal" not in fake_pyfetch.calls[0]


async def test_huge_timeout_is_capped_to_int32_ms(fake_pyfetch, fake_abort_signal):
    # setTimeout delays above 2^31-1 ms overflow and fire at once, aborting the request
    await _handle(
        _request_with_timeout({"connect": None, "read": 1e10, "write": None, "pool": None})
    )
    assert fake_abort_signal.timeouts == [_MAX_ABORT_SIGNAL_MS]
    assert fake_pyfetch.calls[0]["signal"] == f"signal-{_MAX_ABORT_SIGNAL_MS}"


class RaisingPyfetch:
    def __init__(self, exc: BaseException):
        self.exc = exc

    async def __call__(self, url: str, **kwargs: Any):
        raise self.exc


def _install_raising_pyfetch(monkeypatch, exc: BaseException) -> None:
    monkeypatch.setattr(_httpx_fetch, "pyfetch", RaisingPyfetch(exc))


async def test_fetch_failure_maps_to_httpx_connect_error(monkeypatch):
    # pyodide surfaces JS fetch rejections as OSError; the base client can only classify
    # httpx exceptions, so the transport maps OSError to httpx errors
    _install_raising_pyfetch(monkeypatch, OSError("TypeError: Failed to fetch"))
    with pytest.raises(httpx.ConnectError, match="Failed to fetch") as excinfo:
        await _handle(httpx.Request("GET", "http://h:8080/v1/meta"))
    assert isinstance(excinfo.value.__cause__, OSError)


async def test_fetch_abort_with_deadline_maps_to_read_timeout(monkeypatch, fake_abort_signal):
    # AbortSignal.timeout firing surfaces as an OSError subclass mentioning the abort;
    # with a deadline set this must classify as a timeout, not a connection error
    _install_raising_pyfetch(monkeypatch, OSError("AbortError: signal timed out"))
    with pytest.raises(httpx.ReadTimeout, match="signal timed out"):
        await _handle(
            _request_with_timeout({"connect": None, "read": 0.5, "write": None, "pool": None})
        )


async def test_fetch_failure_with_deadline_but_no_timeout_message_stays_connect_error(
    monkeypatch, fake_abort_signal
):
    # nearly every weaviate request sets a read deadline; a plain network failure on
    # such a request must remain a connection error, not become a timeout
    _install_raising_pyfetch(monkeypatch, OSError("TypeError: Failed to fetch"))
    with pytest.raises(httpx.ConnectError, match="Failed to fetch"):
        await _handle(
            _request_with_timeout({"connect": None, "read": 30.0, "write": None, "pool": None})
        )


async def test_fetch_abort_without_deadline_stays_connect_error(monkeypatch, missing_js):
    # without our deadline (no js bridge -> no signal), an abort is a connection error
    _install_raising_pyfetch(monkeypatch, OSError("AbortError: signal timed out"))
    with pytest.raises(httpx.ConnectError):
        await _handle(
            _request_with_timeout({"connect": None, "read": 0.5, "write": None, "pool": None})
        )


async def test_empty_oserror_str_keeps_repr_detail(monkeypatch):
    _install_raising_pyfetch(monkeypatch, OSError())
    with pytest.raises(httpx.ConnectError) as excinfo:
        await _handle(httpx.Request("GET", "http://h:8080/v1/meta"))
    assert "OSError" in str(excinfo.value)


async def test_crlf_in_header_value_rejected(fake_pyfetch):
    request = httpx.Request(
        "GET", "http://h:8080/v1/meta", headers={"x-key": "val\r\nx-injected: evil"}
    )
    with pytest.raises(httpx.LocalProtocolError):
        await _handle(request)
    assert fake_pyfetch.calls == []


# ---------------------------------------------------------------------------
# install semantics, against this interpreter's real installation
# ---------------------------------------------------------------------------


def test_bootstrap_installed_fetch_transport():
    # the import at the top ran the real bootstrap, which replaces Pyodide's jsfetch transport
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
    # the module keeps the pre-patch method while installed, so the restore can be
    # checked by identity even though the install happened at import time
    original = _httpx_fetch._original_handle_async_request
    assert original is not None
    patched_method = httpx.AsyncHTTPTransport.handle_async_request
    try:
        weaviate_client_web.uninstall_fetch_transport()
        assert not weaviate_client_web.is_fetch_transport_installed()
        assert httpx.AsyncHTTPTransport.handle_async_request is original
        assert httpx.AsyncHTTPTransport.handle_async_request is not patched_method
        weaviate_client_web.uninstall_fetch_transport()  # no-op when not installed
        assert httpx.AsyncHTTPTransport.handle_async_request is original
    finally:
        weaviate_client_web.install_fetch_transport()
    assert weaviate_client_web.is_fetch_transport_installed()
    assert (
        getattr(httpx.AsyncHTTPTransport.handle_async_request, "__weaviate_fetch_shim__", False)
        is True
    )


async def test_installed_transport_routes_async_client_through_pyfetch(fake_pyfetch):
    # the globally installed transport (no custom transport argument) must reach pyfetch
    fake_pyfetch.response = FakeFetchResponse(
        status=200, headers={"content-type": "application/json"}, body=b'{"ok": true}'
    )
    async with httpx.AsyncClient() as client:
        response = await client.get("http://h:8080/v1/meta")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert fake_pyfetch.calls and fake_pyfetch.calls[0]["url"] == "http://h:8080/v1/meta"
