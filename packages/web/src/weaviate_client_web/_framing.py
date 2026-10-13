"""grpc-web binary framing (application/grpc-web+proto).

Each frame is a 1-byte flag, a 4-byte big-endian length and the payload. Flag 0x80 marks
the trailer frame (an HTTP/1-style header block); 0x01 (compressed) is not supported.
"""

import struct
from typing import Dict, Iterator, List, Tuple

_FLAG_TRAILER = 0x80
_FLAG_COMPRESSED = 0x01
_KNOWN_FLAGS = _FLAG_TRAILER | _FLAG_COMPRESSED
_HEADER = struct.Struct(">BI")  # 1 flag byte + 4-byte big-endian length
_SINGLE_VALUE_TRAILERS = ("grpc-status", "grpc-message")


class FrameError(ValueError):
    """The body is not a well-formed grpc-web response."""


class UnknownFrameFlagError(FrameError):
    """A flag byte outside the grpc-web set: the body is not grpc-web framing (JSON, HTML, …)."""


class TruncatedFrameError(FrameError):
    """The body ends before the length its frame header announces."""


def encode_message(payload: bytes) -> bytes:
    """Frame a single (uncompressed) protobuf payload for sending."""
    return _HEADER.pack(0x00, len(payload)) + payload


def iter_frames(buf: bytes) -> Iterator[Tuple[int, bytes]]:
    """Yield ``(flag, payload)`` for each frame in a grpc-web response body."""
    off, n = 0, len(buf)
    while off < n:
        # Validate the flag before the length so a text body ('{', '<') is reported as
        # non-grpc-web rather than as a truncated frame with a garbage length.
        flag = buf[off]
        if flag & ~_KNOWN_FLAGS:
            raise UnknownFrameFlagError(f"unknown grpc-web frame flag 0x{flag:02x} at byte {off}")
        if off + 5 > n:
            raise TruncatedFrameError(f"truncated grpc-web frame header at byte {off}")
        _, length = _HEADER.unpack_from(buf, off)
        off += 5
        if off + length > n:
            raise TruncatedFrameError(
                f"truncated grpc-web frame: header announces {length} bytes, {n - off} remain"
            )
        yield flag, buf[off : off + length]
        off += length


def parse_trailers(raw: bytes) -> Dict[str, str]:
    """Parse a trailer payload into a lower-cased dict; accepts CRLF or LF line ends.

    Undecodable bytes are replaced, so an odd grpc-message never drops grpc-status.
    Conflicting repeats of grpc-status or grpc-message raise FrameError.
    """
    out: Dict[str, str] = {}
    for line in raw.split(b"\n"):
        line = line.rstrip(b"\r")
        if not line:
            continue
        key, _, value = line.partition(b":")
        name = key.strip().decode("utf-8", "replace").lower()
        text = value.strip().decode("utf-8", "replace")
        if name in _SINGLE_VALUE_TRAILERS and out.get(name, text) != text:
            raise FrameError(f"conflicting {name} values in the grpc-web trailer frame")
        out[name] = text
    return out


def split_response(body: bytes) -> Tuple[List[bytes], Dict[str, str]]:
    """Split a grpc-web body into message payloads and trailers.

    Rejects a second trailer frame, which could overwrite an error grpc-status.
    """
    messages: List[bytes] = []
    trailers: Dict[str, str] = {}
    seen_trailer = False
    for flag, payload in iter_frames(body):
        if flag & _FLAG_TRAILER:
            if flag & _FLAG_COMPRESSED:
                raise FrameError(
                    "compressed grpc-web trailer frames are not supported by this transport"
                )
            if seen_trailer:
                raise FrameError("second trailer frame in a grpc-web response")
            trailers = parse_trailers(payload)
            seen_trailer = True
        elif flag & _FLAG_COMPRESSED:
            raise FrameError(
                "compressed grpc-web message frames are not supported by this transport"
            )
        elif seen_trailer:
            raise FrameError("message frame after the trailer frame")
        else:
            messages.append(payload)
    return messages, trailers
