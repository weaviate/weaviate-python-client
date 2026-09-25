"""grpc-web channel: the grpc.aio channel methods the client uses.

unary_unary POSTs grpc-web through a pluggable sender; stream_stream (BatchStream) raises.
"""

import asyncio
import base64
import math
import sys
import urllib.parse
from typing import Any, Callable, Dict, List, Optional

from ._framing import TruncatedFrameError, UnknownFrameFlagError, encode_message, split_response
from ._sender import Sender, pyfetch_sender
from ._shim import AioChannel, AioRpcError, StatusCode, status_from_int

_default_sender: Sender = pyfetch_sender


def set_sender(sender: Sender) -> None:
    """Override the default async sender used by new channels (tests)."""
    global _default_sender
    _default_sender = sender


def get_sender() -> Sender:
    return _default_sender


# grpc-timeout is at most 8 digits plus a unit; anything longer is rejected by the server.
_GRPC_TIMEOUT_MAX = 100_000_000


def _encode_timeout(seconds: Optional[float]) -> Optional[str]:
    """Encode seconds as a grpc-timeout value: at most 8 digits, unit m/S/M, rounded up.

    Returns None (no deadline) for None, non-finite values and anything beyond 99,999,999
    minutes. Never uses H: vanguard rejects values above 8H.
    """
    if seconds is None or not math.isfinite(seconds):
        return None
    if seconds / 60 >= _GRPC_TIMEOUT_MAX:
        # past the minute range there is no encodable deadline; checked before the
        # multiplication below, which overflows to infinity for huge finite values
        return None
    for amount, unit in ((seconds * 1000, "m"), (seconds, "S"), (seconds / 60, "M")):
        value = max(1, math.ceil(amount))
        if value < _GRPC_TIMEOUT_MAX:
            return f"{value}{unit}"
    return None


# gRPC spec: keys are lower-case [0-9a-z_.-], ASCII values are printable (0x20-0x7E).
_METADATA_KEY_CHARS = frozenset("0123456789abcdefghijklmnopqrstuvwxyz_.-")


def _is_legal_metadata(name: str, text: str) -> bool:
    return (
        bool(name)
        and all(c in _METADATA_KEY_CHARS for c in name)
        and all(" " <= c <= "~" for c in text)
    )


def _normalize_path_prefix(path_prefix: Optional[str]) -> str:
    """One leading slash, no trailing or repeated slashes, no surrounding whitespace.

    ``""`` (also for ``None`` or a blank value) means native gRPC paths.
    """
    segments = [part for part in (path_prefix or "").strip().split("/") if part]
    return "/" + "/".join(segments) if segments else ""


def _fold_metadata(headers: Dict[str, str], metadata: Any) -> None:
    """Fold gRPC call metadata (``[(key, value), ...]``) into fetch headers.

    Binary ``-bin`` keys are base64-encoded as grpc-web requires. Keys and values outside
    the gRPC spec raise ``ValueError`` before any I/O, as native grpcio does.
    """
    if not metadata:
        return
    for key, value in metadata:
        name = key.lower()
        if name.endswith("-bin"):
            raw = value if isinstance(value, (bytes, bytearray)) else str(value).encode()
            text = base64.b64encode(raw).decode("ascii")
        else:
            text = value if isinstance(value, str) else str(value)
        # grpcio's metadata validation, redone here: fetch would reject some of these
        # values synchronously, as a transport error.
        if not _is_legal_metadata(name, text):
            raise ValueError(f"Illegal character in gRPC metadata {name!r}")
        headers[name] = text


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

    Calling it raises immediately, before the ``async for`` in ``connect/v4.py`` begins
    iterating.
    """

    def __init__(self, path: str) -> None:
        self._path = path

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        # batch.dynamic()/fixed_size()/rate_limit() are sync-only, so not suggested here.
        raise RuntimeError(
            f"Bidirectional streaming RPC {self._path!r} (server-side batching / "
            "BatchStream) is not supported over grpc-web. Use "
            "collection.data.insert_many() instead of batch.stream()."
        )


class GrpcWebChannel(AioChannel):
    """grpc.aio channel that sends unary RPCs as grpc-web."""

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
        self._path_prefix = _normalize_path_prefix(path_prefix)
        self._sender: Sender = sender or get_sender()
        # Until a first HTTP response arrives, a fetch rejection is most likely
        # deterministic (CORS, wrong host/port) and must not enter the UNAVAILABLE retry loop.
        self._got_response = False

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
        headers: Dict[str, str] = {}
        _fold_metadata(headers, metadata)
        # Set after folding: additional_headers reaches RPCs as call metadata, and a
        # caller's Content-Type/accept must never replace the grpc-web protocol fields.
        headers.update(
            {
                "content-type": "application/grpc-web+proto",
                "accept": "application/grpc-web+proto",
                "x-grpc-web": "1",
                "x-user-agent": "weaviate-client-web",
            }
        )
        grpc_timeout = _encode_timeout(timeout)
        if grpc_timeout is None:
            timeout = None  # None / non-finite: no deadline, server- or client-side
        else:
            headers["grpc-timeout"] = grpc_timeout
            if timeout is not None and timeout <= 0:
                raise _deadline_exceeded(path, timeout)

        url = self._base_url + self._path_prefix + path
        framed = encode_message(payload)

        # The sender enforces the deadline; grpc-timeout binds only the server. Every failure
        # below becomes AioRpcError (CancelledError propagates); only metadata validation
        # above, before I/O, raises ValueError.
        try:
            status, resp_headers, body = await self._sender(url, headers, framed, timeout)
        except AioRpcError:
            raise
        except (asyncio.TimeoutError, TimeoutError) as exc:
            raise _deadline_exceeded(path, timeout) from exc
        except Exception as exc:  # network/transport failure
            # str() of transport errors can be empty (e.g. httpx.ConnectError) — always
            # include the exception type so failures stay diagnosable
            detail = f"{type(exc).__name__}: {exc}" if str(exc) else repr(exc)
            details = f"grpc-web transport error for {path}: {detail}"
            if sys.platform == "emscripten":
                if not self._path_prefix:
                    details += " " + _no_path_prefix_hint()
                if isinstance(exc, OSError):  # how pyfetch reports every fetch rejection
                    details += ". " + _cors_hint()
            # retryable UNAVAILABLE only once this channel has reached the server
            code = StatusCode.UNAVAILABLE if self._got_response else StatusCode.UNKNOWN
            raise AioRpcError(code=code, details=details) from exc
        self._got_response = True

        try:
            return self._handle_response(status, resp_headers, body, deserialize, url)
        except AioRpcError:
            raise
        except Exception as exc:  # malformed framing / status / payload
            raise AioRpcError(
                code=StatusCode.INTERNAL,
                details=f"malformed grpc-web response for {path}: {exc}",
            ) from exc

    @staticmethod
    def _handle_response(
        http_status: int,
        resp_headers: Dict[str, str],
        body: bytes,
        deserialize: Callable[[bytes], Any],
        url: str = "",
    ) -> Any:
        # Real error responses carry non-grpc-web bodies (404 JSON, proxy HTML); keep
        # status, URL and body in the error.
        messages: List[bytes] = []
        trailers: Dict[str, str] = {}
        frame_error: Optional[BaseException] = None
        if body:
            try:
                messages, trailers = split_response(body)
            except Exception as exc:
                frame_error = exc

        raw_status = trailers.get("grpc-status")
        if raw_status is None:
            raw_status = _header_lookup(resp_headers, "grpc-status")
        raw_message = (
            trailers.get("grpc-message") or _header_lookup(resp_headers, "grpc-message") or ""
        )
        message = urllib.parse.unquote(raw_message)

        if raw_status is None:
            # no grpc-status anywhere and either a non-200 or a body that is not
            # grpc-web framing: a gRPC service did not answer this request
            if http_status != 200 or frame_error is not None:
                raise _frame_error_to_rpc(http_status, url, body, frame_error)
            if messages:
                # Every grpc-web unary response must carry a grpc-status (trailer frame
                # or header); a proxy that drops the trailer must not read as success.
                raise AioRpcError(
                    code=StatusCode.INTERNAL,
                    details="grpc-web response missing grpc-status trailers",
                )
            code = StatusCode.OK
        else:
            code = status_from_int(int(raw_status))

        if code is not StatusCode.OK:
            raise AioRpcError(code=code, details=message)
        if frame_error is not None:
            # grpc-status said OK but the body will not parse — report what actually
            # came back rather than a bare "no message frame".
            raise _frame_error_to_rpc(http_status, url, body, frame_error)
        if len(messages) > 1:
            raise AioRpcError(
                code=StatusCode.INTERNAL,
                details=f"unary grpc-web response carried {len(messages)} message frames",
            )
        if not messages:
            details = "grpc-web response contained no message frame"
            if raw_status is None:
                # HTTP 200, no body frames, and no grpc-status anywhere: the classic
                # signature of a trailers-only error response whose grpc-status /
                # grpc-message headers were stripped by CORS in the browser.
                details += (
                    " and no grpc-status was visible. If this is a cross-origin browser "
                    "request, configure the server or proxy to send "
                    "'Access-Control-Expose-Headers: grpc-status, grpc-message' so "
                    "trailers-only error responses are readable."
                )
            raise AioRpcError(code=StatusCode.INTERNAL, details=details)
        return deserialize(messages[0])


_BODY_EXCERPT_LIMIT = 200


def _deadline_exceeded(path: str, timeout: Optional[float]) -> AioRpcError:
    return AioRpcError(
        code=StatusCode.DEADLINE_EXCEEDED,
        details=f"grpc-web request to {path} timed out after {timeout}s",
    )


def _body_excerpt(body: bytes, limit: int = _BODY_EXCERPT_LIMIT) -> str:
    """Render a short, printable, one-line excerpt of a response body for error details.

    The body here is whatever a server or proxy sent — JSON, HTML, or binary — so decode
    leniently and drop non-printables: building an error detail must never itself raise.
    """
    if not body:
        return "<empty>"
    text = body[:limit].decode("utf-8", "replace")
    text = " ".join("".join(ch if ch.isprintable() else " " for ch in text).split())
    if not text:
        return f"<{len(body)} non-printable bytes>"
    return text + ("..." if len(body) > limit else "")


def _no_path_prefix_hint() -> str:
    # Lazy import: this module is imported while ``weaviate/__init__`` is still
    # bootstrapping the shim under Emscripten.
    from weaviate.connect.base import GRPC_WEB_MIN_SERVER_VERSION, GRPC_WEB_SERVER_PATH_PREFIX

    return (
        "(no grpc_path_prefix set — under Pyodide the connect helpers route gRPC to "
        f"the REST endpoint under '{GRPC_WEB_SERVER_PATH_PREFIX}' by themselves, so use "
        "one of them; hand-built ConnectionParams must set "
        f"grpc_path_prefix='{GRPC_WEB_SERVER_PATH_PREFIX}' for Weaviate >= "
        f"{GRPC_WEB_MIN_SERVER_VERSION}, or point grpc_host/grpc_port at a grpc-web "
        "transcoder)"
    )


def _cors_hint() -> str:
    from weaviate.connect.base import GRPC_WEB_CORS_HINT  # lazy: see _no_path_prefix_hint

    return GRPC_WEB_CORS_HINT


def _frame_error_to_rpc(
    http_status: int, url: str, body: bytes, frame_error: Optional[BaseException]
) -> AioRpcError:
    """Choose the error for a body that did not parse as grpc-web frames."""
    if http_status != 200 or isinstance(frame_error, (UnknownFrameFlagError, TruncatedFrameError)):
        return _non_grpc_web_error(http_status, url, body, frame_error)
    # Well-formed grpc-web up to the point of failure: a grpc-web endpoint answered but
    # broke the protocol (compressed frame, message after trailer, …).
    return AioRpcError(
        code=StatusCode.INTERNAL,
        details=f"malformed grpc-web response from {url or '<unknown url>'}: {frame_error}",
    )


def _non_grpc_web_error(
    http_status: int,
    url: str,
    body: bytes,
    frame_error: Optional[BaseException] = None,
) -> AioRpcError:
    """Error for a response that is not usable grpc-web.

    Details start with "HTTP <status>", then the URL and a body excerpt.
    """
    from weaviate.connect.base import GRPC_WEB_MIN_SERVER_VERSION, GRPC_WEB_SERVER_PATH_PREFIX

    truncated = isinstance(frame_error, TruncatedFrameError)
    what = "not a grpc-web response"
    if http_status == 200 and frame_error is not None:
        if truncated:
            what = f"the grpc-web body is truncated ({frame_error})"
        else:
            what = f"the body is not grpc-web framing ({frame_error})"
    # the base client keys its "wrong path / server too old" diagnosis on this
    # "HTTP <status>" text (weaviate.exceptions.WeaviateGRPCUnavailableError)
    parts = [f"HTTP {http_status} from {url or '<unknown url>'}: {what}."]

    if http_status == 404:
        # either cause is possible; the channel does not know the server version
        parts.append(
            "The grpc-web endpoint does not exist at that path: either this Weaviate "
            f"server predates {GRPC_WEB_MIN_SERVER_VERSION}, the first release to serve "
            "grpc-web, or the configured grpc-web path prefix is wrong. Weaviate's prefix "
            f"is '{GRPC_WEB_SERVER_PATH_PREFIX}'."
        )
    elif http_status == 405:
        # a 405 comes only from an existing HTTP route: the prefix points at one
        parts.append(
            "An HTTP route answered instead of the grpc-web endpoint (method not "
            "allowed): the configured grpc-web path prefix is wrong. Weaviate's prefix "
            f"is '{GRPC_WEB_SERVER_PATH_PREFIX}'."
        )
    elif http_status in (502, 503, 504):
        parts.append("Weaviate or the proxy in front of it is unavailable.")
    elif http_status == 200 and truncated:
        parts.append(
            "The response was cut short — a proxy or browser buffering limit, or the "
            "connection dropped mid-response."
        )
    elif http_status == 200:
        parts.append(
            "Something other than a grpc-web endpoint answered — typically a proxy "
            "error page or a single-page-app catch-all route serving index.html. Check "
            f"the grpc-web path prefix (Weaviate's prefix is '{GRPC_WEB_SERVER_PATH_PREFIX}')."
        )
    parts.append(f"Response body: {_body_excerpt(body)}")

    code = StatusCode.INTERNAL if http_status == 200 else _status_from_http(http_status)
    return AioRpcError(code=code, details=" ".join(parts))


def _status_from_http(http_status: int) -> StatusCode:
    """Map an HTTP status to gRPC per the grpc-web spec.

    Adds 405 -> UNIMPLEMENTED: an HTTP route answered, so the path is wrong, as for 404.
    """
    return {
        400: StatusCode.INTERNAL,
        401: StatusCode.UNAUTHENTICATED,
        403: StatusCode.PERMISSION_DENIED,
        404: StatusCode.UNIMPLEMENTED,
        405: StatusCode.UNIMPLEMENTED,
        429: StatusCode.UNAVAILABLE,
        502: StatusCode.UNAVAILABLE,
        503: StatusCode.UNAVAILABLE,
        504: StatusCode.UNAVAILABLE,
    }.get(http_status, StatusCode.UNKNOWN)
