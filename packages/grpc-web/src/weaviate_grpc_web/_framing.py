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
_HEADER = struct.Struct(">BI")  # 1 flag byte + 4-byte big-endian length


def encode_message(payload: bytes) -> bytes:
    """Frame a single (uncompressed) protobuf payload for sending."""
    return _HEADER.pack(0x00, len(payload)) + payload


def iter_frames(buf: bytes) -> Iterator[Tuple[int, bytes]]:
    """Yield ``(flag, payload)`` for each frame in a grpc-web response body."""
    off, n = 0, len(buf)
    while off + 5 <= n:
        flag, length = _HEADER.unpack_from(buf, off)
        off += 5
        if off + length > n:
            raise ValueError("truncated grpc-web frame")
        yield flag, buf[off : off + length]
        off += length
    if off != n:
        raise ValueError("trailing bytes after final grpc-web frame")


def parse_trailers(raw: bytes) -> Dict[str, str]:
    """Parse a trailer frame payload into a lower-cased header dict."""
    out: Dict[str, str] = {}
    for line in raw.split(b"\r\n"):
        if not line:
            continue
        key, _, value = line.partition(b":")
        out[key.strip().decode("ascii").lower()] = value.strip().decode("ascii")
    return out


def split_response(body: bytes) -> Tuple[List[bytes], Dict[str, str]]:
    """Split a grpc-web response body into message payloads and trailers."""
    messages: List[bytes] = []
    trailers: Dict[str, str] = {}
    for flag, payload in iter_frames(body):
        if flag & _FLAG_TRAILER:
            trailers.update(parse_trailers(payload))
        elif flag & _FLAG_COMPRESSED:
            raise ValueError(
                "compressed grpc-web message frames are not supported by this transport"
            )
        else:
            messages.append(payload)
    return messages, trailers
