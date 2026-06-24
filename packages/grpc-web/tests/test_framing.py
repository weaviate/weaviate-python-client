import struct

import pytest

from weaviate_grpc_web._framing import (
    encode_message,
    iter_frames,
    parse_trailers,
    split_response,
)


def _frame(payload: bytes, flag: int = 0x00) -> bytes:
    return struct.pack(">BI", flag, len(payload)) + payload


def test_encode_message_round_trip():
    framed = encode_message(b"hello")
    frames = list(iter_frames(framed))
    assert frames == [(0x00, b"hello")]


def test_split_response_message_and_trailer():
    body = _frame(b"payload") + _frame(b"grpc-status:0\r\ngrpc-message:\r\n", 0x80)
    messages, trailers = split_response(body)
    assert messages == [b"payload"]
    assert trailers["grpc-status"] == "0"
    assert trailers["grpc-message"] == ""


def test_split_response_multiple_messages():
    body = _frame(b"a") + _frame(b"bb") + _frame(b"grpc-status:0\r\n", 0x80)
    messages, trailers = split_response(body)
    assert messages == [b"a", b"bb"]
    assert trailers["grpc-status"] == "0"


def test_split_response_trailers_only():
    body = _frame(b"grpc-status:7\r\ngrpc-message:denied\r\n", 0x80)
    messages, trailers = split_response(body)
    assert messages == []
    assert trailers == {"grpc-status": "7", "grpc-message": "denied"}


def test_parse_trailers_lowercases_keys():
    parsed = parse_trailers(b"Grpc-Status:0\r\nGrpc-Message:ok\r\n")
    assert parsed == {"grpc-status": "0", "grpc-message": "ok"}


def test_truncated_frame_raises():
    framed = encode_message(b"hello")[:-2]
    with pytest.raises(ValueError):
        list(iter_frames(framed))


def test_compressed_message_frame_rejected():
    body = _frame(b"x", 0x01)
    with pytest.raises(ValueError):
        split_response(body)
