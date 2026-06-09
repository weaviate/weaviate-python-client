"""The grpc-web channel and multicallables.

:class:`GrpcWebChannel` implements the small slice of the ``grpc.aio`` channel interface
that ``weaviate``'s generated stub and ``ConnectionV4`` actually use — ``unary_unary``,
``stream_stream`` and ``close`` — by framing requests as grpc-web and POSTing them via a
pluggable async sender. It subclasses the shim's ``grpc.aio.Channel`` (:class:`AioChannel`)
so the ``isinstance(..., grpc.aio.Channel)`` assertions in ``connect/v4.py`` hold.

Only unary RPCs are supported (Search, Aggregate, TenantsGet, BatchObjects,
BatchReferences, BatchDelete, and the unary health check). ``stream_stream`` (the bidi
``BatchStream`` used by opt-in server-side batching) cannot work over grpc-web/fetch and
raises a clear error.
"""

import base64
import urllib.parse
from typing import Any, Callable, Dict, Optional

from ._framing import encode_message, split_response
from ._sender import Sender, pyfetch_sender
from ._shim import AioChannel, AioRpcError, StatusCode, status_from_int

# Module-level default sender; overridable for tests / non-browser runtimes.
_default_sender: Sender = pyfetch_sender


def set_sender(sender: Sender) -> None:
    """Override the default async sender used by new channels (tests/integration)."""
    global _default_sender
    _default_sender = sender


def get_sender() -> Sender:
    return _default_sender


def _encode_timeout(seconds: float) -> str:
    """Encode a timeout as a grpc-timeout header value (``<positive int><unit>``)."""
    millis = max(1, int(seconds * 1000))
    if millis < 100_000_000:
        return f"{millis}m"
    return f"{max(1, int(seconds))}S"


def _fold_metadata(headers: Dict[str, str], metadata: Any) -> None:
    """Fold gRPC call metadata (``[(key, value), ...]``) into fetch headers.

    Binary ``-bin`` keys are base64-encoded as grpc-web requires.
    """
    if not metadata:
        return
    for key, value in metadata:
        name = key.lower()
        if name.endswith("-bin"):
            raw = value if isinstance(value, (bytes, bytearray)) else str(value).encode()
            headers[name] = base64.b64encode(raw).decode("ascii")
        else:
            headers[name] = value if isinstance(value, str) else str(value)


def _header_lookup(headers: Dict[str, str], name: str) -> Optional[str]:
    target = name.lower()
    for key, value in headers.items():
        if key.lower() == target:
            return value
    return None


class _UnaryUnaryMultiCallable:
    """Awaitable multicallable bound by ``WeaviateStub.__init__``.

    Called as ``await mc(request, metadata=..., timeout=...)`` (and, for the health
    check, as ``mc(request, timeout=...)`` with no metadata).
    """

    def __init__(
        self,
        channel: "GrpcWebChannel",
        path: str,
        request_serializer: Callable[[Any], bytes],
        response_deserializer: Callable[[bytes], Any],
    ) -> None:
        self._channel = channel
        self._path = path
        self._serialize = request_serializer
        self._deserialize = response_deserializer

    async def __call__(
        self,
        request: Any,
        *,
        metadata: Any = None,
        timeout: Optional[float] = None,
        credentials: Any = None,
        wait_for_ready: Any = None,
        compression: Any = None,
    ) -> Any:
        payload = self._serialize(request)
        return await self._channel._unary(self._path, payload, self._deserialize, metadata, timeout)


class _UnsupportedStreamMultiCallable:
    """Placeholder for ``stream_stream`` (bidirectional streaming).

    Calling it raises immediately, before the ``async for`` in ``connect/v4.py:1243``
    begins iterating.
    """

    def __init__(self, path: str) -> None:
        self._path = path

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        raise RuntimeError(
            f"Bidirectional streaming RPC {self._path!r} (server-side batching / "
            "BatchStream) is not supported over grpc-web/fetch. Use insert_many(), or "
            "batch.dynamic() / fixed_size() / rate_limit(), instead of batch.stream()."
        )


class GrpcWebChannel(AioChannel):
    """grpc-web/fetch implementation of the async grpc channel slice the client uses."""

    def __init__(
        self,
        target: Optional[str],
        secure: bool,
        options: Any = None,
        path_prefix: str = "",
        sender: Optional[Sender] = None,
    ) -> None:
        if not target:
            raise ValueError("GrpcWebChannel requires a target (host:port)")
        scheme = "https" if secure else "http"
        self._base_url = f"{scheme}://{target}"
        # Normalize to a single leading slash and no trailing slash; "" == native path.
        cleaned = (path_prefix or "").strip("/")
        self._path_prefix = f"/{cleaned}" if cleaned else ""
        self._sender: Sender = sender or get_sender()

    def unary_unary(
        self,
        method: str,
        request_serializer: Callable[[Any], bytes],
        response_deserializer: Callable[[bytes], Any],
        _registered_method: bool = False,
    ) -> _UnaryUnaryMultiCallable:
        return _UnaryUnaryMultiCallable(self, method, request_serializer, response_deserializer)

    def stream_stream(
        self,
        method: str,
        request_serializer: Callable[[Any], bytes],
        response_deserializer: Callable[[bytes], Any],
        _registered_method: bool = False,
    ) -> _UnsupportedStreamMultiCallable:
        return _UnsupportedStreamMultiCallable(method)

    async def close(self, grace: Optional[float] = None) -> None:
        # Nothing to tear down: each call is an independent fetch.
        return None

    async def _unary(
        self,
        path: str,
        payload: bytes,
        deserialize: Callable[[bytes], Any],
        metadata: Any,
        timeout: Optional[float],
    ) -> Any:
        headers: Dict[str, str] = {
            "content-type": "application/grpc-web+proto",
            "accept": "application/grpc-web+proto",
            "x-grpc-web": "1",
            "x-user-agent": "weaviate-python-grpc-web",
        }
        _fold_metadata(headers, metadata)
        if timeout is not None:
            headers["grpc-timeout"] = _encode_timeout(timeout)

        url = self._base_url + self._path_prefix + path
        status, resp_headers, body = await self._sender(
            url, headers, encode_message(payload), timeout
        )
        return self._handle_response(status, resp_headers, body, deserialize)

    @staticmethod
    def _handle_response(
        http_status: int,
        resp_headers: Dict[str, str],
        body: bytes,
        deserialize: Callable[[bytes], Any],
    ) -> Any:
        messages, trailers = split_response(body) if body else ([], {})

        raw_status = trailers.get("grpc-status")
        if raw_status is None:
            raw_status = _header_lookup(resp_headers, "grpc-status")
        raw_message = (
            trailers.get("grpc-message") or _header_lookup(resp_headers, "grpc-message") or ""
        )
        message = urllib.parse.unquote(raw_message)

        if raw_status is None:
            if http_status != 200:
                raise AioRpcError(
                    code=_status_from_http(http_status),
                    details=f"HTTP {http_status} from grpc-web endpoint",
                )
            code = StatusCode.OK
        else:
            code = status_from_int(int(raw_status))

        if code is not StatusCode.OK:
            raise AioRpcError(code=code, details=message)
        if not messages:
            raise AioRpcError(
                code=StatusCode.INTERNAL,
                details="grpc-web response contained no message frame",
            )
        return deserialize(messages[0])


def _status_from_http(http_status: int) -> StatusCode:
    """Map an HTTP status to a gRPC status when no grpc-status is present.

    Mirrors the grpc-web spec's HTTP-to-gRPC code mapping.
    """
    return {
        400: StatusCode.INTERNAL,
        401: StatusCode.UNAUTHENTICATED,
        403: StatusCode.PERMISSION_DENIED,
        404: StatusCode.UNIMPLEMENTED,
        429: StatusCode.UNAVAILABLE,
        502: StatusCode.UNAVAILABLE,
        503: StatusCode.UNAVAILABLE,
        504: StatusCode.UNAVAILABLE,
    }.get(http_status, StatusCode.UNKNOWN)
