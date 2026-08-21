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

import asyncio
import base64
import math
import sys
import urllib.parse
from typing import Any, Callable, Dict, List, Optional

from ._framing import TruncatedFrameError, UnknownFrameFlagError, encode_message, split_response
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


# grpc-timeout is at most 8 digits plus a unit; anything longer is rejected by the server.
_GRPC_TIMEOUT_MAX = 100_000_000


def _encode_timeout(seconds: Optional[float]) -> Optional[str]:
    """Encode a timeout as a grpc-timeout header value; ``None`` means no deadline.

    ``None``, non-finite values and anything beyond 99,999,999 minutes (~190 years) carry
    no deadline. Rounds up so we never advertise a shorter deadline than requested (which
    would risk premature server-side cancellation), moving to a coarser unit
    (m -> S -> M) to stay within 8 digits. Hours are never emitted: grpc-web transcoders
    (vanguard) reject any H value above 8H with HTTP 400.
    """
    if seconds is None or not math.isfinite(seconds):
        return None
    for amount, unit in ((seconds * 1000, "m"), (seconds, "S"), (seconds / 60, "M")):
        value = max(1, math.ceil(amount))
        if value < _GRPC_TIMEOUT_MAX:
            return f"{value}{unit}"
    return None


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
            text = base64.b64encode(raw).decode("ascii")
        else:
            text = value if isinstance(value, str) else str(value)
        # This path bypasses h11/grpcio's header validation, so keep their defence here.
        if any(c in name or c in text for c in ("\r", "\n", "\0")):
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
        # NOTE: do not recommend batch.dynamic()/fixed_size()/rate_limit() here — those
        # are sync-client-only APIs and do not exist on the async client, which is the
        # only client supported under WASM.
        raise RuntimeError(
            f"Bidirectional streaming RPC {self._path!r} (server-side batching / "
            "BatchStream) is not supported over grpc-web/fetch. Use "
            "collection.data.insert_many() instead of batch.stream()."
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
            "x-user-agent": "weaviate-client-web",
        }
        _fold_metadata(headers, metadata)
        grpc_timeout = _encode_timeout(timeout)
        if grpc_timeout is None:
            timeout = None  # None / non-finite: no deadline, server- or client-side
        else:
            headers["grpc-timeout"] = grpc_timeout

        url = self._base_url + self._path_prefix + path
        framed = encode_message(payload)

        # Send. Enforce a client-side deadline (the grpc-timeout header is server-side
        # only; pyfetch ignores its timeout arg, so without this a stalled request could
        # hang forever). Any transport/parse failure is surfaced as AioRpcError; the only
        # non-gRPC error a caller can see is the ValueError from metadata validation
        # above, raised before any I/O (as native grpcio does).
        try:
            send = self._sender(url, headers, framed, timeout)
            if timeout is not None:
                status, resp_headers, body = await asyncio.wait_for(send, timeout)
            else:
                status, resp_headers, body = await send
        except AioRpcError:
            raise
        except asyncio.TimeoutError as exc:
            raise AioRpcError(
                code=StatusCode.DEADLINE_EXCEEDED,
                details=f"grpc-web request to {path} timed out after {timeout}s",
            ) from exc
        except Exception as exc:  # network/transport failure -> retryable UNAVAILABLE
            # str() of transport errors can be empty (e.g. httpx.ConnectError) — always
            # include the exception type so failures stay diagnosable
            detail = f"{type(exc).__name__}: {exc}" if str(exc) else repr(exc)
            details = f"grpc-web transport error for {path}: {detail}"
            if not self._path_prefix and sys.platform == "emscripten":
                details += " " + _no_path_prefix_hint()
            raise AioRpcError(code=StatusCode.UNAVAILABLE, details=details) from exc

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
        # A frame-parse failure must never decide the outcome by itself: real error
        # responses carry non-grpc-web bodies (Weaviate's 404 JSON, an nginx page), and
        # the HTTP status, URL and the server's own text must survive into the error.
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
            # No grpc-status anywhere AND either a non-200 or a body that is not
            # grpc-web framing: a gRPC service did not answer this request at all.
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
                    "request, configure the grpc-web proxy to send "
                    "'Access-Control-Expose-Headers: grpc-status, grpc-message' so "
                    "trailers-only error responses are readable."
                )
            raise AioRpcError(code=StatusCode.INTERNAL, details=details)
        return deserialize(messages[0])


_BODY_EXCERPT_LIMIT = 200


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
    from weaviate.exceptions import GRPC_WEB_MIN_SERVER_VERSION, GRPC_WEB_SERVER_PATH_PREFIX

    return (
        "(no grpc_path_prefix set — under WebAssembly the connect helpers route gRPC to "
        f"the REST endpoint under '{GRPC_WEB_SERVER_PATH_PREFIX}' by themselves, so use "
        "one of them; hand-built ConnectionParams must set "
        f"grpc_path_prefix='{GRPC_WEB_SERVER_PATH_PREFIX}' for Weaviate >= "
        f"{GRPC_WEB_MIN_SERVER_VERSION}, or point grpc_host/grpc_port at a grpc-web "
        "transcoder)"
    )


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
    """Build the error for a response that is not a usable grpc-web response.

    Details always begin with ``HTTP <status>`` and carry the request URL plus a body
    excerpt (``weaviate/connect`` matches on that prefix). The status alone rarely
    separates "endpoint missing" from "proxy misconfigured"; the server's own body
    text usually does.
    """
    truncated = isinstance(frame_error, TruncatedFrameError)
    what = "not a grpc-web response"
    if http_status == 200 and frame_error is not None:
        if truncated:
            what = f"the grpc-web body is truncated ({frame_error})"
        else:
            what = f"the body is not grpc-web framing ({frame_error})"
    parts = [f"HTTP {http_status} from {url or '<unknown url>'}: {what}."]

    if http_status == 404:
        # Two candidate causes, and the channel cannot tell them apart (it does not know
        # the server version) — name both rather than guess.
        parts.append(
            "The grpc-web endpoint does not exist at that path: either this Weaviate "
            "server predates 1.38.3, the first release to serve grpc-web natively, or "
            "the configured grpc-web path prefix is wrong for the proxy in front of it. "
            "Weaviate's native prefix is '/v1/grpc-web'."
        )
    elif http_status == 405:
        # A 405 can only come from an existing HTTP route: the prefix points at one.
        parts.append(
            "An HTTP route answered instead of the grpc-web endpoint (method not "
            "allowed): the configured grpc-web path prefix is wrong. Weaviate's native "
            "prefix is '/v1/grpc-web'."
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
            "the grpc-web path prefix (Weaviate's native prefix is '/v1/grpc-web')."
        )
    parts.append(f"Response body: {_body_excerpt(body)}")

    code = StatusCode.INTERNAL if http_status == 200 else _status_from_http(http_status)
    return AioRpcError(code=code, details=" ".join(parts))


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
