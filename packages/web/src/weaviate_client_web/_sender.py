"""HTTP senders for the grpc-web transport.

A *sender* is ``async def sender(url, headers, body, timeout) -> (status, headers, body)``.
The default uses ``pyodide.http.pyfetch``; tests inject one with
:func:`weaviate_client_web.set_sender`.
"""

from typing import Awaitable, Callable, Dict, Optional, Tuple

from pyodide.http import pyfetch  # type: ignore[import-not-found]

Sender = Callable[
    [str, Dict[str, str], bytes, Optional[float]],
    Awaitable[Tuple[int, Dict[str, str], bytes]],
]


async def pyfetch_sender(
    url: str, headers: Dict[str, str], body: bytes, timeout: Optional[float]
) -> Tuple[int, Dict[str, str], bytes]:
    """Default browser sender.

    ``pyfetch`` has no timeout parameter of its own; the call deadline is enforced by
    ``GrpcWebChannel._unary`` via ``asyncio.wait_for``.
    """
    response = await pyfetch(url, method="POST", headers=headers, body=body)
    data = await response.bytes()
    try:
        resp_headers = dict(response.headers)
    except Exception:  # pragma: no cover - header shape varies across Pyodide versions
        resp_headers = {}
    return int(response.status), resp_headers, data
