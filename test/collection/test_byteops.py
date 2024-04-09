from weaviate.collections.queries.byteops import _ByteOps


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


def test_decode_bools():
    assert _ByteOps.decode_bools(b"") == []
    assert _ByteOps.decode_bools(b"\x01\x00") == [True, False]


def test_decode_strings():
    assert _ByteOps.decode_strings(b"") == []
    assert _ByteOps.decode_strings(b"hello,world") == ["hello", "world"]


def test_generate_strings():
    assert list(_ByteOps.generate_strings(b"")) == []

    count = 0
    for _ in _ByteOps.generate_strings(b""):
        count += 1
    assert count == 0

    generator = _ByteOps.generate_strings(b"hello,world")
    assert next(generator) == "hello"
    assert next(generator) == "world"
