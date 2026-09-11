r"""grpc-web binary framing (``application/grpc-web+proto``).

A grpc-web message frame is a 1-byte flag + 4-byte big-endian length + payload:

    +--------+----------------+----------------------+
    | flag   | length (uint32)| payload (length bytes)|
    +--------+----------------+----------------------+

The flag's high bit (``0x80``) marks a trailer frame whose payload is an
HTTP/1-style header block (``grpc-status: 0\\r\\ngrpc-message: ...``). The low bit
(``0x01``) marks a compressed message, which this transport neither sends nor
accepts. A unary grpc-web response body is one or more message frames followed by
exactly one trailer frame (or a "trailers-only" response carrying the status in
the HTTP headers, handled by the caller).
"""

import struct
from typing import Dict, Iterator, List, Tuple

_FLAG_TRAILER = 0x80
_FLAG_COMPRESSED = 0x01
_KNOWN_FLAGS = _FLAG_TRAILER | _FLAG_COMPRESSED
_HEADER = struct.Struct(">BI")  # 1 flag byte + 4-byte big-endian length


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
    """Parse a trailer frame payload into a lower-cased header dict.

    Decoded leniently on both sides of the colon: a proxy that does not percent-encode
    ``grpc-message``, or a server error quoting a UTF-8 collection / tenant / property
    name, puts raw non-ASCII bytes in the trailer, and one odd key must not discard the
    ``grpc-status`` travelling with it. Lines are CRLF-terminated by spec; bare LF is
    accepted.
    """
    out: Dict[str, str] = {}
    for line in raw.split(b"\n"):
        line = line.rstrip(b"\r")
        if not line:
            continue
        key, _, value = line.partition(b":")
        name = key.strip().decode("utf-8", "replace").lower()
        out[name] = value.strip().decode("utf-8", "replace")
    return out


def split_response(body: bytes) -> Tuple[List[bytes], Dict[str, str]]:
    """Split a grpc-web response body into message payloads and trailers."""
    messages: List[bytes] = []
    trailers: Dict[str, str] = {}
    seen_trailer = False
    for flag, payload in iter_frames(body):
        if flag & _FLAG_TRAILER:
            trailers.update(parse_trailers(payload))
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
