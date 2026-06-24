"""fetch-based httpx transport for Pyodide/Emscripten.

The base client's REST path uses ``httpx.AsyncClient`` with explicit
``httpx.AsyncHTTPTransport`` mounts (``weaviate/connect/v4.py``). httpcore opens raw
sockets, which do not exist under WASM, so without this module every REST call
(``is_ready``, collection config, batch references, …) fails with an empty connection
error even though the grpc-web data path works.

Installing reroutes ``AsyncHTTPTransport.handle_async_request`` through the browser's
``fetch`` via ``pyodide.http.pyfetch`` — the same install-globally-under-Emscripten
philosophy as the grpc shim in ``_shim.py``. Responses are fully buffered, which matches
how the base client consumes them (JSON bodies, no streaming).

NOTE: Pyodide >= 0.27 distributes a patched httpx whose ``AsyncHTTPTransport`` already
routes through JS ``fetch`` natively (``httpx/_transports/jsfetch.py``) with streaming
support and a proper connect/read timeout split. When that build is detected, installing
is skipped — overwriting it would replace a better implementation. This transport is the
fallback for environments where httpx resolved from PyPI (httpcore + raw sockets).

Known divergences from native httpx (acceptable for the weaviate client's usage):
- the browser's fetch follows redirects internally, so httpx never sees a 3xx;
- multi-value response headers (e.g. Set-Cookie) are folded into one value;
- responses are fully buffered (no streaming).
"""

import importlib.util
import sys
from typing import Callable, Dict, Optional

import httpx

_installed = False
_original_handle_async_request: Optional[Callable] = None

# Hop-by-hop / connection-managed headers that the browser's fetch controls itself.
# Browsers silently drop forbidden headers, but Node's undici (used by the CPython/Node
# test path) rejects some of them outright, so strip them before handing off.
_FETCH_MANAGED_HEADERS = {
    "host",
    "connection",
    "accept-encoding",
    "content-length",
    "transfer-encoding",
}

# Response headers describing the wire encoding of the body. fetch decompresses
# responses transparently, so the bytes handed to httpx are already plain; passing the
# original content-encoding through makes httpx run its decoders over them again and
# raise DecodingError, and the original content-length no longer matches the body.
# (Browsers usually hide content-encoding on CORS responses, which is why this never
# fired live — same-origin and Node fetch do expose it.)
_FETCH_DECODED_RESPONSE_HEADERS = {
    "content-encoding",
    "content-length",
}

_TIMEOUT_HINTS = ("timeout", "timed out", "abort")


async def _read_request_body(request: httpx.Request) -> bytes:
    try:
        return request.content
    except httpx.RequestNotRead:
        return await request.aread()


def _pick_timeout(request: httpx.Request) -> Optional[float]:
    """Pick the effective deadline from httpx's timeout extension.

    httpx populates ``extensions['timeout']`` with connect/read/write/pool values; the
    read timeout is what the weaviate client configures per request. ``get(...) or``
    chains would silently skip an explicit 0, so check for None instead.
    """
    timeouts = request.extensions.get("timeout") or {}
    for key in ("read", "connect", "pool"):
        value = timeouts.get(key)
        if value is not None:
            return value
    return None


def _map_fetch_error(
    e: BaseException, request: httpx.Request, deadline_set: bool
) -> httpx.TransportError:
    """Translate a pyfetch failure into httpx's exception taxonomy.

    Pyodide surfaces every JS fetch rejection (network down, DNS, CORS, CSP, an
    AbortSignal firing) as OSError — or pyodide.http.AbortError, an OSError subclass —
    never as an httpx exception. Without this mapping the base client cannot classify
    failures (WeaviateConnectionError/WeaviateTimeoutError) and best-effort callers that
    swallow httpx.RequestError break.
    """
    msg = str(e) or repr(e)
    if deadline_set and any(hint in msg.lower() for hint in _TIMEOUT_HINTS):
        return httpx.ReadTimeout(msg, request=request)
    return httpx.ConnectError(msg, request=request)


def _validate_header(name: str, value: str) -> None:
    # httpx.Request accepts CR/LF in header values and relies on h11 to reject them at
    # send time; this transport bypasses h11, so mirror that defence here rather than
    # delegating it entirely to the JS runtime's fetch.
    if any(c in name or c in value for c in ("\r", "\n", "\0")):
        raise httpx.LocalProtocolError(f"Illegal character in header {name!r}")


async def _fetch_handle_async_request(
    self: httpx.AsyncHTTPTransport, request: httpx.Request
) -> httpx.Response:
    from pyodide.http import pyfetch  # type: ignore[import-not-found]

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

    timeout = _pick_timeout(request)
    deadline_set = False
    if timeout is not None and timeout > 0:
        try:
            from js import AbortSignal  # type: ignore[import-not-found]

            kwargs["signal"] = AbortSignal.timeout(int(timeout * 1000))
            deadline_set = True
        except Exception:  # pragma: no cover - AbortSignal.timeout availability varies
            pass

    try:
        response = await pyfetch(str(request.url), method=request.method, headers=headers, **kwargs)
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
    return httpx.Response(
        status_code=int(response.status),
        headers=resp_headers,
        content=data,
        request=request,
    )


# sentinel so other packages (and uninstall) can recognise the patched method
_fetch_handle_async_request.__weaviate_fetch_shim__ = True  # type: ignore[attr-defined]


def _platform_httpx_has_fetch_support() -> bool:
    """True when the running httpx is Pyodide's distributed build.

    That build replaces the httpcore transport with a native JS-fetch one
    (httpx/_transports/jsfetch.py), so the weaviate REST path already works without
    this shim — and works better (streaming, connect/read timeout split).
    """
    try:
        return importlib.util.find_spec("httpx._transports.jsfetch") is not None
    except (ImportError, ValueError):  # pragma: no cover - exotic import states
        return False


def install_fetch_transport(force: bool = False) -> None:
    """Patch ``httpx.AsyncHTTPTransport`` to send requests through ``fetch``.

    Installs only under Emscripten unless ``force=True`` (CPython testing, where a
    ``pyodide`` stub must be importable), and is skipped when httpx itself already has
    fetch support (Pyodide's distributed build). Idempotent.
    """
    global _installed, _original_handle_async_request
    if _installed:
        return
    if not force:
        if sys.platform != "emscripten":
            return
        if _platform_httpx_has_fetch_support():
            return
    # Fail fast: the handler imports pyfetch per request, so a missing pyodide module
    # would otherwise surface as a confusing ModuleNotFoundError on the first request.
    from pyodide.http import pyfetch  # type: ignore[import-not-found]  # noqa: F401

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
