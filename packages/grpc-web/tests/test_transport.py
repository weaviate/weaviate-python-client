"""In-process tests for the grpc-web channel/multicallable.

These exercise the transport classes directly (they import their grpc base classes from
``weaviate_grpc_web._shim``, not from ``sys.modules['grpc']``), so no shim install is
needed and the real ``grpc`` in the dev environment is left untouched.
"""

import asyncio
import struct
from typing import Dict, List, Optional, Tuple

import pytest

from weaviate_grpc_web._channel import GrpcWebChannel, set_sender
from weaviate_grpc_web._shim import AioChannel, AioRpcError, StatusCode


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
    # mirrors connect/v4.py:316 — request + timeout, no metadata
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


def test_http_error_without_grpc_status_maps_to_code():
    channel = _channel(FakeSender(status=403, headers={}, body=b""))
    mc = channel.unary_unary("/svc/M", lambda x: x, lambda b: b)
    with pytest.raises(AioRpcError) as excinfo:
        asyncio.run(mc(b"q"))
    assert excinfo.value.code() is StatusCode.PERMISSION_DENIED


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


def test_close_is_awaitable_noop():
    channel = _channel(FakeSender())
    assert asyncio.run(channel.close()) is None


def test_set_sender_overrides_default():
    sender = FakeSender(body=_ok_response(b"y"))
    set_sender(sender)
    try:
        channel = GrpcWebChannel("h:1", secure=False)  # no explicit sender
        mc = channel.unary_unary("/svc/M", lambda x: x, lambda b: b)
        assert asyncio.run(mc(b"q")) == b"y"
    finally:
        # restore the real default so other tests/processes are unaffected
        from weaviate_grpc_web._sender import pyfetch_sender

        set_sender(pyfetch_sender)
