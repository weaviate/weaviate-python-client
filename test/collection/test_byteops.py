import pytest

from weaviate.collections.grpc.query import _QueryGRPC
from weaviate.collections.grpc.shared import _ByteOps, _Pack, _Unpack
from weaviate.exceptions import WeaviateInvalidInputError
from weaviate.util import _ServerVersion


def test_decode_float32s():
    assert _ByteOps.decode_float32s(b"") == []
    assert _ByteOps.decode_float32s(b"\x00\x00\x80?\x00\x00\x00@\x00\x00\x00\x00") == [
        1.0,
        2.0,
        0.0,
    ]


def test_decode_float64s():
    assert _ByteOps.decode_float64s(b"") == []
    assert _ByteOps.decode_float64s(
        b"\x00\x00\x00\x00\x00\x00\xf0?\x00\x00\x00\x00\x00\x00\x00@\x00\x00\x00\x00\x00\x00\x00\x00"
    ) == [1.0, 2.0, 0.0]


def test_decode_int64s():
    assert _ByteOps.decode_int64s(b"") == []
    assert _ByteOps.decode_int64s(
        b"\x01\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00"
    ) == [1, 2]


def test_multi_vector_pack_round_trip():
    vector = [[1.0, 2.0], [3.0, 4.0]]

    assert _Unpack.multi(_Pack.multi(vector)) == vector


def test_multi_vector_pack_rejects_ragged_vectors():
    with pytest.raises(WeaviateInvalidInputError, match="consistent dimensions"):
        _Pack.multi([[1.0, 2.0], [3.0]])


def test_near_vector_request_rejects_ragged_multi_vector():
    query = _QueryGRPC(
        _ServerVersion.from_string("1.29.0"),
        "TestCollection",
        None,
        None,
        True,
        True,
        True,
    )

    with pytest.raises(WeaviateInvalidInputError, match="consistent dimensions"):
        query.near_vector(near_vector=[[1.0, 2.0], [3.0]])
