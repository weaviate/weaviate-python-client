"""fetch-based httpx.AsyncHTTPTransport for Pyodide, where httpcore has no sockets.

Replaces Pyodide's bundled jsfetch transport, which fails on body-less HEAD/204 responses
and ignores read timeouts. Differs from native httpx: fetch follows redirects itself,
multi-value headers are folded, and bodies are fully buffered.
"""

import math
import sys
from typing import Callable, Dict, Optional

import httpx
from pyodide.http import pyfetch  # type: ignore[import-not-found]

_installed = False
_original_handle_async_request: Optional[Callable] = None

# Hop-by-hop / connection-managed headers that the browser's fetch controls itself.
# Browsers silently drop forbidden headers, but Node's undici (behind pyfetch in the
# Node-based test harness) rejects some of them outright, so strip them before handing off.
_FETCH_MANAGED_HEADERS = {
    "host",
    "connection",
    "accept-encoding",
    "content-length",
    "transfer-encoding",
}

# fetch has already decoded the body; passing content-encoding/length through would make
# httpx decode it again.
_FETCH_DECODED_RESPONSE_HEADERS = {
    "content-encoding",
    "content-length",
}

_TIMEOUT_HINTS = ("timeout", "timed out", "abort")

# JS timers take a signed 32-bit millisecond delay; anything larger overflows and fires
# immediately, so a huge timeout would abort every request at once.
_MAX_ABORT_SIGNAL_MS = 2**31 - 1


async def _read_request_body(request: httpx.Request) -> bytes:
    try:
        return request.content
    except httpx.RequestNotRead:
        return await request.aread()


def _pick_timeout(request: httpx.Request) -> Optional[float]:
    """The request deadline: httpx's ``read`` timeout only (None = no deadline).

    ``connect`` and ``pool`` have no meaning under fetch.
    """
    timeouts = request.extensions.get("timeout") or {}
    return timeouts.get("read")


def _abort_signal_ms(timeout: Optional[float]) -> Optional[int]:
    """Milliseconds for an abort timer, or None for no deadline (None, negative, non-finite).

    Zero is immediate, as in httpx; positive values round up; capped at 2**31-1.
    """
    if timeout is None or not math.isfinite(timeout) or timeout < 0:
        return None
    if timeout >= _MAX_ABORT_SIGNAL_MS / 1000:
        # compared before the multiplication below, which overflows to infinity for
        # huge finite values
        return _MAX_ABORT_SIGNAL_MS
    return min(math.ceil(timeout * 1000), _MAX_ABORT_SIGNAL_MS)


def _map_fetch_error(
    e: BaseException, request: httpx.Request, deadline_set: bool
) -> httpx.TransportError:
    """Map a pyfetch OSError (network, DNS, CORS, CSP, abort) to an httpx error.

    httpx.ReadTimeout if our deadline fired, else httpx.ConnectError.
    """
    msg = str(e) or repr(e)
    if deadline_set and any(hint in msg.lower() for hint in _TIMEOUT_HINTS):
        return httpx.ReadTimeout(msg, request=request)
    return httpx.ConnectError(msg, request=request)


def _validate_header(name: str, value: str) -> None:
    # h11 normally rejects CR/LF/NUL in headers; this transport bypasses h11.
    if any(c in name or c in value for c in ("\r", "\n", "\0")):
        raise httpx.LocalProtocolError(f"Illegal character in header {name!r}")


async def _fetch_handle_async_request(
    self: httpx.AsyncHTTPTransport, request: httpx.Request
) -> httpx.Response:
    headers: Dict[str, str] = {}
    for k, v in request.headers.items():
        if k.lower() in _FETCH_MANAGED_HEADERS:
            continue
        _validate_header(k, v)
        headers[k] = v
    kwargs: Dict[str, object] = {}
    body = await _read_request_body(request)
    if body:
        # fetch rejects GET/HEAD requests that carry a body
        kwargs["body"] = body

    deadline_set = False
    deadline_ms = _abort_signal_ms(_pick_timeout(request))
    if deadline_ms is not None:
        try:
            from js import AbortSignal  # type: ignore[import-not-found]

            kwargs["signal"] = AbortSignal.timeout(deadline_ms)
            deadline_set = True
        except Exception:  # pragma: no cover - AbortSignal.timeout availability varies
            pass

    try:
        response = await pyfetch(str(request.url), method=request.method, headers=headers, **kwargs)
        # A body-less response (HEAD, 204) reads as b"": fetch resolves a null body to
        # an empty ArrayBuffer.
        data = await response.bytes()
    except OSError as e:  # incl. pyodide.http.AbortError
        raise _map_fetch_error(e, request, deadline_set) from e

    try:
        resp_headers = {
            k: v
            for k, v in dict(response.headers).items()
            if k.lower() not in _FETCH_DECODED_RESPONSE_HEADERS
        }
    except Exception:  # pragma: no cover - header shape varies across Pyodide versions
        resp_headers = {}
    # Hand httpx an unread stream, as its own transports do: the client reads it and
    # only then stamps ``response.elapsed``, which the batch-references path relies on.
    return httpx.Response(
        status_code=int(response.status),
        headers=resp_headers,
        stream=httpx.ByteStream(data),
        request=request,
    )


# marker for detecting the patched method (tests, ci/pyodide-e2e)
_fetch_handle_async_request.__weaviate_fetch_shim__ = True  # type: ignore[attr-defined]


def install_fetch_transport() -> None:
    """Patch ``httpx.AsyncHTTPTransport`` to send requests through ``fetch``.

    Installs only under Emscripten (elsewhere httpx's own socket transports work and
    must be left in place). Idempotent.
    """
    global _installed, _original_handle_async_request
    if _installed:
        return
    if sys.platform != "emscripten":
        return
    _original_handle_async_request = httpx.AsyncHTTPTransport.handle_async_request
    httpx.AsyncHTTPTransport.handle_async_request = _fetch_handle_async_request  # type: ignore[method-assign]
    _installed = True


def uninstall_fetch_transport() -> None:
    """Restore the original ``httpx.AsyncHTTPTransport`` behaviour. No-op if not installed."""
    global _installed, _original_handle_async_request
    if not _installed:
        return
    assert _original_handle_async_request is not None
    httpx.AsyncHTTPTransport.handle_async_request = _original_handle_async_request  # type: ignore[method-assign]
    _original_handle_async_request = None
    _installed = False


def is_fetch_transport_installed() -> bool:
    return _installed
