import struct

import pytest

from weaviate_client_web._framing import (
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


def test_parse_trailers_keeps_status_when_message_is_not_ascii():
    # A proxy that does not percent-encode grpc-message, or a server error quoting a
    # UTF-8 collection/tenant name, sends raw non-ASCII bytes. Decoding must not raise:
    # the grpc-status travelling with it is the part the client acts on.
    parsed = parse_trailers("grpc-status:5\r\ngrpc-message:Café not found\r\n".encode("utf-8"))
    assert parsed["grpc-status"] == "5"
    assert parsed["grpc-message"] == "Café not found"


def test_parse_trailers_keeps_status_when_message_is_invalid_utf8():
    # latin-1 (or any non-UTF-8) bytes must degrade to replacement chars, not an error
    parsed = parse_trailers(b"grpc-status:9\r\ngrpc-message:tenant caf\xe9 is COLD\r\n")
    assert parsed["grpc-status"] == "9"
    assert parsed["grpc-message"].startswith("tenant caf")


def test_split_response_survives_non_ascii_trailer():
    body = _frame("grpc-status:7\r\ngrpc-message:accès refusé\r\n".encode("utf-8"), 0x80)
    messages, trailers = split_response(body)
    assert messages == []
    assert trailers["grpc-status"] == "7"


def test_truncated_frame_raises():
    framed = encode_message(b"hello")[:-2]
    with pytest.raises(ValueError):
        list(iter_frames(framed))


def test_compressed_message_frame_rejected():
    body = _frame(b"x", 0x01)
    with pytest.raises(ValueError):
        split_response(body)
