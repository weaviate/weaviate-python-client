"""In-process tests for the grpc-web channel/multicallable.

These exercise the transport classes directly (they import their grpc base classes from
``weaviate_client_web._shim``, not from ``sys.modules['grpc']``), so no shim install is
needed and the real ``grpc`` in the dev environment is left untouched.
"""

import asyncio
import struct
import sys
from typing import Dict, List, Optional, Tuple

import pytest

from weaviate_client_web._channel import (
    GrpcWebChannel,
    _body_excerpt,
    _encode_timeout,
    set_sender,
)
from weaviate_client_web._shim import AioChannel, AioRpcError, StatusCode


def _frame(payload: bytes, flag: int = 0x00) -> bytes:
    return struct.pack(">BI", flag, len(payload)) + payload


def _ok_response(payload: bytes) -> bytes:
    return _frame(payload) + _frame(b"grpc-status:0\r\n", 0x80)


class FakeSender:
    def __init__(
        self, status: int = 200, headers: Optional[Dict[str, str]] = None, body: bytes = b""
    ):
        self.status = status
        self.headers = headers or {}
        self.body = body
        self.calls: List[Tuple[str, Dict[str, str], bytes, Optional[float]]] = []

    async def __call__(self, url, headers, body, timeout):
        self.calls.append((url, headers, body, timeout))
        return self.status, self.headers, self.body


def _channel(sender: FakeSender, secure: bool = False) -> GrpcWebChannel:
    return GrpcWebChannel("example.com:443", secure=secure, sender=sender)


def test_grpcwebchannel_is_grpc_aio_channel():
    assert issubclass(GrpcWebChannel, AioChannel)
    assert isinstance(_channel(FakeSender()), AioChannel)


def test_unary_success_round_trip():
    sender = FakeSender(body=_ok_response(b"reply-bytes"))
    channel = _channel(sender)
    mc = channel.unary_unary(
        "/weaviate.v1.Weaviate/Search",
        request_serializer=lambda x: x,
        response_deserializer=lambda b: b,
        _registered_method=True,
    )

    result = asyncio.run(mc(b"request-bytes", metadata=[("authorization", "Bearer k")], timeout=5))

    assert result == b"reply-bytes"
    url, headers, body, timeout = sender.calls[0]
    assert url == "http://example.com:443/weaviate.v1.Weaviate/Search"
    assert body == _frame(b"request-bytes")
    assert headers["content-type"] == "application/grpc-web+proto"
    assert headers["authorization"] == "Bearer k"
    assert headers["grpc-timeout"] == "5000m"
    assert timeout == 5


def test_secure_channel_uses_https():
    sender = FakeSender(body=_ok_response(b"x"))
    channel = _channel(sender, secure=True)
    mc = channel.unary_unary("/svc/M", lambda x: x, lambda b: b)
    asyncio.run(mc(b"q"))
    assert sender.calls[0][0].startswith("https://example.com:443/")


def test_health_call_without_metadata():
    sender = FakeSender(body=_ok_response(b"pong"))
    channel = _channel(sender)
    mc = channel.unary_unary("/grpc.health.v1.Health/Check", lambda x: x, lambda b: b)
    # mirrors the health check in connect/v4.py — request + timeout, no metadata
    assert asyncio.run(mc(b"ping", timeout=2)) == b"pong"


def test_error_trailer_raises_aiorpcerror():
    body = _frame(b"grpc-status:7\r\ngrpc-message:nope\r\n", 0x80)
    channel = _channel(FakeSender(body=body))
    mc = channel.unary_unary("/svc/M", lambda x: x, lambda b: b)

    with pytest.raises(AioRpcError) as excinfo:
        asyncio.run(mc(b"q"))
    assert excinfo.value.code() is StatusCode.PERMISSION_DENIED
    assert excinfo.value.code().name == "PERMISSION_DENIED"
    assert excinfo.value.details() == "nope"


def test_percent_encoded_grpc_message_decoded():
    body = _frame(b"grpc-status:5\r\ngrpc-message:not%20found\r\n", 0x80)
    channel = _channel(FakeSender(body=body))
    mc = channel.unary_unary("/svc/M", lambda x: x, lambda b: b)
    with pytest.raises(AioRpcError) as excinfo:
        asyncio.run(mc(b"q"))
    assert excinfo.value.details() == "not found"


def test_trailers_only_status_in_http_headers():
    channel = _channel(
        FakeSender(status=200, headers={"grpc-status": "16", "grpc-message": "auth"}, body=b"")
    )
    mc = channel.unary_unary("/svc/M", lambda x: x, lambda b: b)
    with pytest.raises(AioRpcError) as excinfo:
        asyncio.run(mc(b"q"))
    assert excinfo.value.code() is StatusCode.UNAUTHENTICATED


# --- non-grpc-web responses -------------------------------------------------------
#
# Every real error response carries a body, and none of them is grpc-web framing. The
# bodies below are verbatim shapes seen in the wild (an empty error body is the one
# shape no server or proxy produces).

# Weaviate's own 404, verbatim from a 1.39.0 server asked for the wrong prefix.
WEAVIATE_404_JSON = (
    b'{"code":404,"message":"path /grpc-web/grpc.health.v1.Health/Check was not found"}'
)
NGINX_502_HTML = (
    b"<html>\r\n<head><title>502 Bad Gateway</title></head>\r\n<body>\r\n"
    b"<center><h1>502 Bad Gateway</h1></center>\r\n<hr><center>nginx/1.27.3</center>\r\n"
    b"</body>\r\n</html>\r\n"
)
NGINX_404_HTML = (
    b"<html>\r\n<head><title>404 Not Found</title></head>\r\n<body>\r\n"
    b"<center><h1>404 Not Found</h1></center>\r\n<hr><center>nginx/1.27.3</center>\r\n"
    b"</body>\r\n</html>\r\n"
)
# A single-page app's catch-all route answers 200 with index.html for unknown paths.
SPA_INDEX_HTML = (
    b'<!doctype html>\n<html lang="en">\n  <head>\n    <title>My App</title>\n'
    b'    <script type="module" src="/assets/index-4f21a0.js"></script>\n'
    b'  </head>\n  <body><div id="root"></div></body>\n</html>\n'
)


def _details_of(status, body, headers=None, path="/grpc.health.v1.Health/Check"):
    """Run one request against a canned HTTP response and return the AioRpcError."""
    channel = _channel(FakeSender(status=status, headers=headers or {}, body=body))
    mc = channel.unary_unary(path, lambda x: x, lambda b: b)
    with pytest.raises(AioRpcError) as excinfo:
        asyncio.run(mc(b"q"))
    return excinfo.value


def test_weaviate_404_json_names_both_candidate_causes():
    # A 404 means EITHER the server predates the native /v1/grpc-web endpoint OR the
    # configured path prefix is wrong. The channel cannot tell which, so it must say both.
    err = _details_of(404, WEAVIATE_404_JSON, {"content-type": "application/json"})
    details = err.details()

    assert err.code() is StatusCode.UNIMPLEMENTED
    assert details.startswith("HTTP 404 ")
    assert "/grpc.health.v1.Health/Check" in details  # the request path
    assert "1.38.3" in details  # candidate 1: server too old
    assert "path prefix" in details  # candidate 2: wrong prefix
    assert "/v1/grpc-web" in details  # the native prefix, spelled out
    assert "was not found" in details  # the server's own explanation
    assert "malformed grpc-web response" not in details


def test_nginx_502_maps_to_unavailable_so_the_client_retries():
    # weaviate/retry.py retries UNAVAILABLE and nothing else; a gateway error arriving
    # as INTERNAL is silently un-retried, which is the regression this pins.
    err = _details_of(502, NGINX_502_HTML)
    assert err.code() is StatusCode.UNAVAILABLE
    assert err.details().startswith("HTTP 502 ")
    assert "502 Bad Gateway" in err.details()


@pytest.mark.parametrize("status", [503, 504])
def test_gateway_errors_are_unavailable(status):
    err = _details_of(status, b"<html><body>upstream down</body></html>")
    assert err.code() is StatusCode.UNAVAILABLE


def test_nginx_404_html_is_reported_as_an_http_404():
    err = _details_of(404, NGINX_404_HTML)
    assert err.code() is StatusCode.UNIMPLEMENTED
    assert err.details().startswith("HTTP 404 ")
    assert "404 Not Found" in err.details()
    assert "malformed grpc-web response" not in err.details()


def test_405_names_the_wrong_prefix():
    # a 405 can only come from an existing HTTP route (measured live: a prefix pointing
    # at /v1/objects answers "method POST is not allowed"), so the prefix is wrong
    err = _details_of(405, b'{"code":405,"message":"method POST is not allowed, but [GET] are"}')
    assert err.details().startswith("HTTP 405 ")
    assert "path prefix" in err.details()
    assert "/v1/grpc-web" in err.details()
    assert "method POST is not allowed" in err.details()


def test_truncated_grpc_web_body_is_reported_as_truncated_not_as_wrong_prefix():
    # a valid frame header whose payload was cut short: the endpoint IS grpc-web, so the
    # SPA / path-prefix hint would send the user the wrong way
    body = _ok_response(b"reply-bytes")[:-6]
    err = _details_of(200, body)
    assert err.code() is StatusCode.INTERNAL
    assert "truncated" in err.details()
    assert "cut short" in err.details()
    assert "single-page-app" not in err.details()
    assert "path prefix" not in err.details()


def test_spa_html_body_is_not_reported_as_truncated():
    # text bodies decode to an unknown flag byte and a garbage length; they must read as
    # "not grpc-web framing", never as a truncated grpc-web body
    err = _details_of(200, SPA_INDEX_HTML)
    assert "truncated" not in err.details()
    assert "not grpc-web framing" in err.details()


def test_message_frame_after_trailer_is_internal():
    body = _frame(b"a") + _frame(b"grpc-status:0\r\n", 0x80) + _frame(b"late")
    err = _details_of(200, body)
    assert err.code() is StatusCode.INTERNAL
    assert "malformed grpc-web response" in err.details()
    assert "after the trailer" in err.details()
    assert "single-page-app" not in err.details()


def test_multiple_message_frames_in_unary_response_is_internal():
    # a unary RPC has exactly one message; silently taking the first would hide a proxy
    # or server that streams several
    body = _frame(b"a") + _frame(b"bb") + _frame(b"grpc-status:0\r\n", 0x80)
    err = _details_of(200, body)
    assert err.code() is StatusCode.INTERNAL
    assert "2 message frames" in err.details()


def test_error_status_wins_over_multiple_message_frames():
    body = _frame(b"a") + _frame(b"bb") + _frame(b"grpc-status:5\r\ngrpc-message:gone\r\n", 0x80)
    err = _details_of(200, body)
    assert err.code() is StatusCode.NOT_FOUND
    assert err.details() == "gone"


def test_spa_fallback_html_200_is_distinguishable_from_a_404():
    # An HTTP 200 serving index.html is the other half of a wrong path prefix: the app's
    # catch-all route answers instead of Weaviate. It must not read as malformed framing.
    err = _details_of(200, SPA_INDEX_HTML)
    details = err.details()

    assert details.startswith("HTTP 200 ")
    assert "<!doctype html>" in details
    assert "single-page-app" in details  # names the actual cause
    assert "malformed grpc-web response" not in details
    # distinguishable from the 404 case, not the same generic message
    assert details != _details_of(404, NGINX_404_HTML).details()


def test_401_json_body_maps_to_unauthenticated():
    err = _details_of(401, b'{"error":[{"message":"anonymous access not enabled"}]}')
    assert err.code() is StatusCode.UNAUTHENTICATED
    assert err.details().startswith("HTTP 401 ")
    assert "anonymous access not enabled" in err.details()


def test_403_error_body_reaches_details():
    # regression: the response body is the most actionable part of the error and must
    # survive into details() rather than being parsed as frames and discarded
    err = _details_of(403, b'{"code":403,"message":"forbidden: rbac denied"}')
    assert err.code() is StatusCode.PERMISSION_DENIED
    assert "forbidden: rbac denied" in err.details()


def test_error_body_excerpt_is_capped():
    err = _details_of(500, b"E" * 5000)
    details = err.details()
    assert "EEEE" in details
    assert details.endswith("...")
    assert len(details) < 600  # the 5000-byte body is excerpted, not pasted in


def test_binary_error_body_does_not_break_the_error():
    # a proxy answering with a binary payload must not raise UnicodeDecodeError while
    # the error message is being built
    err = _details_of(502, b"\xff\xfe\x00\x01\x02")
    assert err.code() is StatusCode.UNAVAILABLE
    assert err.details().startswith("HTTP 502 ")


def test_non_200_with_valid_grpc_web_trailers_still_uses_grpc_status():
    # guard on the fix's shape: the HTTP status must not shadow a real grpc-status that
    # a proxy shipped alongside a non-200
    err = _details_of(500, _frame(b"grpc-status:7\r\ngrpc-message:denied\r\n", 0x80))
    assert err.code() is StatusCode.PERMISSION_DENIED
    assert err.details() == "denied"


def test_non_ascii_grpc_message_preserves_the_status():
    # a trailer carrying raw UTF-8 (an un-percent-encoded proxy, or an error quoting a
    # collection name) must not degrade to INTERNAL and lose grpc-status
    body = _frame("grpc-status:5\r\ngrpc-message:collection Café not found\r\n".encode(), 0x80)
    err = _details_of(200, body)
    assert err.code() is StatusCode.NOT_FOUND
    assert "Caf" in err.details()


def test_invalid_utf8_grpc_message_preserves_the_status():
    # latin-1 bytes are not valid UTF-8; the status must still survive
    body = _frame(b"grpc-status:9\r\ngrpc-message:tenant caf\xe9 is COLD\r\n", 0x80)
    err = _details_of(200, body)
    assert err.code() is StatusCode.FAILED_PRECONDITION
    assert "tenant caf" in err.details()


def test_binary_metadata_base64_encoded():
    sender = FakeSender(body=_ok_response(b"x"))
    channel = _channel(sender)
    mc = channel.unary_unary("/svc/M", lambda x: x, lambda b: b)
    asyncio.run(mc(b"q", metadata=[("trace-bin", b"\x00\x01\x02")]))
    assert sender.calls[0][1]["trace-bin"] == "AAEC"


def test_stream_stream_raises_clear_error():
    channel = _channel(FakeSender())
    mc = channel.stream_stream("/weaviate.v1.Weaviate/BatchStream", lambda x: x, lambda b: b)
    with pytest.raises(RuntimeError) as excinfo:
        mc(request_iterator=iter([]), timeout=5, metadata=None)
    assert "not supported over grpc-web" in str(excinfo.value)


def test_timeout_maps_to_deadline_exceeded():
    async def slow_sender(url, headers, body, timeout):
        await asyncio.sleep(0.5)
        return 200, {}, _ok_response(b"x")

    channel = GrpcWebChannel("h:1", secure=False, sender=slow_sender)
    mc = channel.unary_unary("/svc/M", lambda x: x, lambda b: b)
    with pytest.raises(AioRpcError) as excinfo:
        asyncio.run(mc(b"q", timeout=0.01))
    assert excinfo.value.code() is StatusCode.DEADLINE_EXCEEDED


def test_transport_exception_maps_to_unavailable():
    async def boom(url, headers, body, timeout):
        raise ConnectionError("connection refused")

    channel = GrpcWebChannel("h:1", secure=False, sender=boom)
    mc = channel.unary_unary("/svc/M", lambda x: x, lambda b: b)
    with pytest.raises(AioRpcError) as excinfo:
        asyncio.run(mc(b"q"))
    assert excinfo.value.code() is StatusCode.UNAVAILABLE
    assert "ConnectionError: connection refused" in str(excinfo.value.details())


def test_transport_exception_with_empty_str_keeps_type():
    # httpx transport errors commonly stringify to '' — the detail must still name them
    async def boom(url, headers, body, timeout):
        raise ConnectionError()

    channel = GrpcWebChannel("h:1", secure=False, sender=boom)
    mc = channel.unary_unary("/svc/M", lambda x: x, lambda b: b)
    with pytest.raises(AioRpcError) as excinfo:
        asyncio.run(mc(b"q"))
    assert "ConnectionError" in str(excinfo.value.details())


def test_empty_ok_response_hints_at_cors_expose_headers():
    # HTTP 200, empty body, no grpc-status anywhere: the shape of a trailers-only error
    # whose grpc-status/grpc-message headers were stripped by CORS
    channel = _channel(FakeSender(status=200, headers={}, body=b""))
    mc = channel.unary_unary("/svc/M", lambda x: x, lambda b: b)
    with pytest.raises(AioRpcError) as excinfo:
        asyncio.run(mc(b"q"))
    assert excinfo.value.code() is StatusCode.INTERNAL
    assert "Access-Control-Expose-Headers" in str(excinfo.value.details())


def test_empty_ok_response_with_grpc_status_has_no_cors_hint():
    # when grpc-status WAS visible (status 0, no frames), it is a malformed response,
    # not a CORS problem — the hint must not appear
    channel = _channel(FakeSender(status=200, headers={"grpc-status": "0"}, body=b""))
    mc = channel.unary_unary("/svc/M", lambda x: x, lambda b: b)
    with pytest.raises(AioRpcError) as excinfo:
        asyncio.run(mc(b"q"))
    assert excinfo.value.code() is StatusCode.INTERNAL
    assert "Access-Control-Expose-Headers" not in str(excinfo.value.details())


def test_message_frame_without_grpc_status_is_internal_not_success():
    # HTTP 200 with a valid message frame but no grpc-status anywhere (e.g. a proxy
    # dropped the trailer frame) must be an error, never a fabricated success
    channel = _channel(FakeSender(status=200, headers={}, body=_frame(b"reply-bytes")))
    mc = channel.unary_unary("/svc/M", lambda x: x, lambda b: b)
    with pytest.raises(AioRpcError) as excinfo:
        asyncio.run(mc(b"q"))
    assert excinfo.value.code() is StatusCode.INTERNAL
    assert "missing grpc-status" in str(excinfo.value.details())


def test_message_frame_with_grpc_status_header_still_succeeds():
    # trailers-only-in-headers responses (grpc-status as an HTTP header, no trailer
    # frame) remain valid per the grpc-web contract
    channel = _channel(
        FakeSender(status=200, headers={"grpc-status": "0"}, body=_frame(b"reply-bytes"))
    )
    mc = channel.unary_unary("/svc/M", lambda x: x, lambda b: b)
    assert asyncio.run(mc(b"q")) == b"reply-bytes"


def test_stream_stream_error_recommends_insert_many_only():
    # batch.dynamic()/fixed_size()/rate_limit() do not exist on the async client (the
    # only one supported under WASM), so the error must not recommend them
    channel = _channel(FakeSender())
    mc = channel.stream_stream("/weaviate.v1.Weaviate/BatchStream", lambda x: x, lambda b: b)
    with pytest.raises(RuntimeError) as excinfo:
        mc(request_iterator=iter([]), timeout=5, metadata=None)
    assert "insert_many" in str(excinfo.value)
    for sync_only in ("dynamic", "fixed_size", "rate_limit"):
        assert sync_only not in str(excinfo.value)


def test_malformed_frame_maps_to_internal():
    # A 3-byte body cannot contain even a 5-byte frame header -> framing ValueError.
    channel = _channel(FakeSender(body=b"\x00\x00\x00"))
    mc = channel.unary_unary("/svc/M", lambda x: x, lambda b: b)
    with pytest.raises(AioRpcError) as excinfo:
        asyncio.run(mc(b"q"))
    assert excinfo.value.code() is StatusCode.INTERNAL


def test_malformed_grpc_status_maps_to_internal():
    body = _frame(b"grpc-status:notanint\r\n", 0x80)
    channel = _channel(FakeSender(body=body))
    mc = channel.unary_unary("/svc/M", lambda x: x, lambda b: b)
    with pytest.raises(AioRpcError) as excinfo:
        asyncio.run(mc(b"q"))
    assert excinfo.value.code() is StatusCode.INTERNAL


def test_grpc_timeout_header_rounds_up():
    sender = FakeSender(body=_ok_response(b"x"))
    channel = _channel(sender)
    mc = channel.unary_unary("/svc/M", lambda x: x, lambda b: b)
    # 123.4ms must round UP to 124ms (never advertise a shorter deadline than requested).
    asyncio.run(mc(b"q", timeout=0.1234))
    assert sender.calls[0][1]["grpc-timeout"] == "124m"


def test_body_excerpt_empty_and_non_printable():
    assert _body_excerpt(b"") == "<empty>"
    assert _body_excerpt(b"\x00\x01\x02\x7f") == "<4 non-printable bytes>"
    assert _body_excerpt(b"ok\x00\x01") == "ok"


@pytest.mark.parametrize(
    "seconds,expected",
    [
        (None, None),
        (float("inf"), None),
        (float("nan"), None),
        (0, "1m"),
        (0.1234, "124m"),
        (5, "5000m"),
        (99_999, "99999000m"),
        (100_000, "100000S"),  # 1e8 ms would be 9 digits
        (1e8, "1666667M"),  # 1e8 s would be 9 digits
        (1e9, "16666667M"),
        (5_999_999_940, "99999999M"),  # the largest deadline that still fits in minutes
        (1e10, None),  # would need hours, which transcoders reject above 8H: no deadline
        (1e15, None),
    ],
)
def test_encode_timeout_stays_within_eight_digits(seconds, expected):
    encoded = _encode_timeout(seconds)
    assert encoded == expected
    if encoded is not None:
        assert len(encoded) <= 9  # 8 digits + unit
        assert not encoded.endswith("H")


def test_infinite_timeout_sends_no_deadline():
    # Timeout(query=inf): neither a grpc-timeout header nor a client-side wait
    sender = FakeSender(body=_ok_response(b"x"))
    channel = _channel(sender)
    mc = channel.unary_unary("/svc/M", lambda x: x, lambda b: b)
    assert asyncio.run(mc(b"q", timeout=float("inf"))) == b"x"
    _, headers, _, timeout = sender.calls[0]
    assert "grpc-timeout" not in headers
    assert timeout is None


def test_huge_timeout_uses_minutes_then_no_deadline():
    # 1e8 s in milliseconds is 12 digits; the server rejects more than 8 ("timeout is
    # too long", HTTP 400) and transcoders reject hour values above 8H, so past the
    # minute range the request carries no deadline at all
    sender = FakeSender(body=_ok_response(b"x"))
    channel = _channel(sender)
    mc = channel.unary_unary("/svc/M", lambda x: x, lambda b: b)
    asyncio.run(mc(b"q", timeout=1e8))
    asyncio.run(mc(b"q", timeout=1e9))
    asyncio.run(mc(b"q", timeout=1e10))
    assert sender.calls[0][1]["grpc-timeout"] == "1666667M"
    assert sender.calls[1][1]["grpc-timeout"] == "16666667M"
    assert "grpc-timeout" not in sender.calls[2][1]
    assert sender.calls[2][3] is None  # no client-side wait either


@pytest.mark.parametrize("bad", ["val\r\nx-injected: evil", "val\nx", "v\0"])
def test_crlf_in_metadata_rejected(bad):
    sender = FakeSender(body=_ok_response(b"x"))
    channel = _channel(sender)
    mc = channel.unary_unary("/svc/M", lambda x: x, lambda b: b)
    with pytest.raises(ValueError, match="Illegal character"):
        asyncio.run(mc(b"q", metadata=[("x-key", bad)]))
    with pytest.raises(ValueError, match="Illegal character"):
        asyncio.run(mc(b"q", metadata=[("x-key\r\n", "v")]))
    assert sender.calls == []


def _unavailable_details(monkeypatch, path_prefix, platform):
    async def boom(url, headers, body, timeout):
        raise ConnectionError("Failed to fetch")

    monkeypatch.setattr(sys, "platform", platform)
    channel = GrpcWebChannel("h:50051", secure=False, sender=boom, path_prefix=path_prefix)
    mc = channel.unary_unary("/svc/M", lambda x: x, lambda b: b)
    with pytest.raises(AioRpcError) as excinfo:
        asyncio.run(mc(b"q"))
    assert excinfo.value.code() is StatusCode.UNAVAILABLE
    return excinfo.value.details()


def test_unavailable_without_path_prefix_under_emscripten_hints_at_grpc_path_prefix(monkeypatch):
    # the connect helpers always set the prefix under Emscripten, so a prefix-less channel
    # here means hand-built ConnectionParams; the error must say what to do instead
    details = _unavailable_details(monkeypatch, path_prefix="", platform="emscripten")
    assert "grpc_path_prefix='/v1/grpc-web'" in details
    assert "1.38.3" in details
    assert "connect helpers" in details


def test_unavailable_with_path_prefix_has_no_prefix_hint(monkeypatch):
    details = _unavailable_details(monkeypatch, path_prefix="/v1/grpc-web", platform="emscripten")
    assert "no grpc_path_prefix" not in details


def test_unavailable_without_path_prefix_off_emscripten_has_no_prefix_hint(monkeypatch):
    # on CPython an empty prefix against a transcoder is the normal configuration
    details = _unavailable_details(monkeypatch, path_prefix="", platform="linux")
    assert "no grpc_path_prefix" not in details


def test_close_is_awaitable_noop():
    channel = _channel(FakeSender())
    assert asyncio.run(channel.close()) is None


def test_path_prefix_prepended_to_url():
    sender = FakeSender(body=_ok_response(b"r"))
    channel = GrpcWebChannel(
        "example.com:8090", secure=False, sender=sender, path_prefix="/grpc-web"
    )
    mc = channel.unary_unary("/weaviate.v1.Weaviate/Search", lambda x: x, lambda b: b)
    asyncio.run(mc(b"q"))
    assert sender.calls[0][0] == "http://example.com:8090/grpc-web/weaviate.v1.Weaviate/Search"


@pytest.mark.parametrize(
    "raw,expected_url",
    [
        ("grpc-web", "http://h:1/grpc-web/svc/M"),
        ("/grpc-web/", "http://h:1/grpc-web/svc/M"),
        ("/a/b", "http://h:1/a/b/svc/M"),
        ("", "http://h:1/svc/M"),
    ],
)
def test_path_prefix_normalized_in_url(raw, expected_url):
    sender = FakeSender(body=_ok_response(b"r"))
    channel = GrpcWebChannel("h:1", secure=False, sender=sender, path_prefix=raw)
    mc = channel.unary_unary("/svc/M", lambda x: x, lambda b: b)
    asyncio.run(mc(b"q"))
    assert sender.calls[0][0] == expected_url


def test_shim_factory_extracts_path_prefix_option():
    from weaviate_client_web._shim import _aio_insecure_channel

    with_prefix = _aio_insecure_channel(
        target="h:1",
        options=[("grpc.max_send_message_length", 1), ("grpc-web.path_prefix", "/grpc-web")],
    )
    assert with_prefix._path_prefix == "/grpc-web"

    without_prefix = _aio_insecure_channel(
        target="h:1", options=[("grpc.max_send_message_length", 1)]
    )
    assert without_prefix._path_prefix == ""


def test_set_sender_overrides_default():
    sender = FakeSender(body=_ok_response(b"y"))
    set_sender(sender)
    try:
        channel = GrpcWebChannel("h:1", secure=False)  # no explicit sender
        mc = channel.unary_unary("/svc/M", lambda x: x, lambda b: b)
        assert asyncio.run(mc(b"q")) == b"y"
    finally:
        # restore the real default so other tests/processes are unaffected
        from weaviate_client_web._sender import pyfetch_sender

        set_sender(pyfetch_sender)
