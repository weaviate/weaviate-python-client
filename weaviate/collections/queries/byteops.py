import struct
from typing import List


class _ByteOps:
    @staticmethod
    def decode_float32s(byte_vector: bytes) -> List[float]:
        return [float(val) for val in struct.unpack(f"{len(byte_vector)//4}f", byte_vector)]

    @staticmethod
    def decode_float64s(byte_vector: bytes) -> List[float]:
        return [float(val) for val in struct.unpack(f"{len(byte_vector)//8}d", byte_vector)]

    @staticmethod
    def decode_int64s(byte_vector: bytes) -> List[int]:
        return [int(val) for val in struct.unpack(f"{len(byte_vector)//8}q", byte_vector)]
