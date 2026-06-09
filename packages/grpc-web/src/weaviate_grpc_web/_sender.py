"""HTTP senders for the grpc-web transport.

A *sender* is ``async def sender(url, headers, body, timeout) -> (status, headers, body)``.
The default uses ``pyodide.http.pyfetch`` (browser fetch); a sender can be injected for
testing or for non-browser runtimes via :func:`weaviate_grpc_web.set_sender`.
"""

from typing import Awaitable, Callable, Dict, Optional, Tuple

Sender = Callable[
    [str, Dict[str, str], bytes, Optional[float]],
    Awaitable[Tuple[int, Dict[str, str], bytes]],
]


async def pyfetch_sender(
    url: str, headers: Dict[str, str], body: bytes, timeout: Optional[float]
) -> Tuple[int, Dict[str, str], bytes]:
    """Default browser sender.

    Imports ``pyodide.http`` lazily so this module stays importable on CPython (where
    ``pyodide`` does not exist).
    """
    from pyodide.http import pyfetch  # type: ignore[import-not-found]

    response = await pyfetch(url, method="POST", headers=headers, body=body)
    data = await response.bytes()
    try:
        resp_headers = dict(response.headers)
    except Exception:  # pragma: no cover - header shape varies across Pyodide versions
        resp_headers = {}
    return int(response.status), resp_headers, data


def make_httpx_sender(client: Optional[object] = None) -> Sender:
    """Build a sender backed by ``httpx.AsyncClient`` for CPython tests/integration.

    Targets a grpc-web transcoder (Envoy / connectrpc vanguard).
    """
    import httpx

    async def _send(
        url: str, headers: Dict[str, str], body: bytes, timeout: Optional[float]
    ) -> Tuple[int, Dict[str, str], bytes]:
        owns_client = client is None
        active = client or httpx.AsyncClient()
        assert isinstance(active, httpx.AsyncClient)
        try:
            response = await active.post(url, headers=headers, content=body, timeout=timeout)
            return (
                response.status_code,
                {k.lower(): v for k, v in response.headers.items()},
                response.content,
            )
        finally:
            if owns_client:
                await active.aclose()

    return _send
