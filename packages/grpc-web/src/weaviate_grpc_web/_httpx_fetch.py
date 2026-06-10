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
"""

import sys
from typing import Dict

import httpx

_installed = False

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


async def _read_request_body(request: httpx.Request) -> bytes:
    try:
        return request.content
    except httpx.RequestNotRead:
        return await request.aread()


async def _fetch_handle_async_request(
    self: httpx.AsyncHTTPTransport, request: httpx.Request
) -> httpx.Response:
    from pyodide.http import pyfetch  # type: ignore[import-not-found]

    headers: Dict[str, str] = {
        k: v for k, v in request.headers.items() if k.lower() not in _FETCH_MANAGED_HEADERS
    }
    kwargs: Dict[str, object] = {}
    body = await _read_request_body(request)
    if body:
        # fetch rejects GET/HEAD requests that carry a body
        kwargs["body"] = body

    timeouts = request.extensions.get("timeout") or {}
    timeout = timeouts.get("read") or timeouts.get("connect") or timeouts.get("pool")
    if timeout:
        try:
            from js import AbortSignal  # type: ignore[import-not-found]

            kwargs["signal"] = AbortSignal.timeout(int(timeout * 1000))
        except Exception:  # pragma: no cover - AbortSignal.timeout availability varies
            pass

    response = await pyfetch(str(request.url), method=request.method, headers=headers, **kwargs)
    data = await response.bytes()
    try:
        resp_headers = dict(response.headers)
    except Exception:  # pragma: no cover - header shape varies across Pyodide versions
        resp_headers = {}
    return httpx.Response(
        status_code=int(response.status),
        headers=resp_headers,
        content=data,
        request=request,
    )


def install_fetch_transport(force: bool = False) -> None:
    """Patch ``httpx.AsyncHTTPTransport`` to send requests through ``fetch``.

    Installs only under Emscripten unless ``force=True`` (CPython testing, where a
    ``pyodide`` stub must be importable). Idempotent.
    """
    global _installed
    if _installed:
        return
    if not force and sys.platform != "emscripten":
        return
    httpx.AsyncHTTPTransport.handle_async_request = _fetch_handle_async_request  # type: ignore[method-assign]
    _installed = True


def is_fetch_transport_installed() -> bool:
    return _installed
