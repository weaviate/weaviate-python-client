"""HTTP senders for the grpc-web transport.

A *sender* is ``async def sender(url, headers, body, timeout) -> (status, headers, body)``;
it enforces ``timeout`` (seconds, ``None`` = no deadline) and raises ``TimeoutError`` when
it expires. The default uses ``pyodide.http.pyfetch``; tests inject one with
:func:`weaviate_client_web.set_sender`.
"""

from typing import Any, Awaitable, Callable, Dict, Optional, Tuple

from pyodide.http import pyfetch  # type: ignore[import-not-found]

from ._httpx_fetch import _abort_signal_ms

Sender = Callable[
    [str, Dict[str, str], bytes, Optional[float]],
    Awaitable[Tuple[int, Dict[str, str], bytes]],
]


async def pyfetch_sender(
    url: str, headers: Dict[str, str], body: bytes, timeout: Optional[float]
) -> Tuple[int, Dict[str, str], bytes]:
    """POST through pyodide.http.pyfetch; raises ``TimeoutError`` when ``timeout`` expires.

    The deadline aborts the fetch; its JS timer is cleared when the call ends.
    """
    kwargs: Dict[str, Any] = {}
    controller = timer = clear_timeout = None
    delay_ms = _abort_signal_ms(timeout)
    if delay_ms is not None:
        from js import AbortController, clearTimeout, setTimeout  # type: ignore[import-not-found]

        controller = AbortController.new()
        clear_timeout = clearTimeout
        timer = setTimeout(controller.abort.bind(controller), delay_ms)
        kwargs["signal"] = controller.signal
    try:
        response = await pyfetch(url, method="POST", headers=headers, body=body, **kwargs)
        data = await response.bytes()
    except OSError as exc:  # pyodide.http.AbortError included
        if controller is not None and controller.signal.aborted:
            raise TimeoutError(f"deadline of {timeout}s exceeded") from exc
        raise
    finally:
        if timer is not None and clear_timeout is not None:
            clear_timeout(timer)
    try:
        resp_headers = dict(response.headers)
    except Exception:  # pragma: no cover - header shape varies across Pyodide versions
        resp_headers = {}
    return int(response.status), resp_headers, data
