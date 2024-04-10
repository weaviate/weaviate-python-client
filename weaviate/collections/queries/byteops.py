import struct
from typing import List


class _ByteOps:
    @staticmethod
    def decode_bools(byte_vector: bytes) -> List[bool]:
        return [byte == 1 for byte in byte_vector]

    @staticmethod
    def decode_float32s(byte_vector: bytes) -> List[float]:
        return list(struct.unpack(f"{len(byte_vector)//4}f", byte_vector))

    @staticmethod
    def decode_float64s(byte_vector: bytes) -> List[float]:
        return list(struct.unpack(f"{len(byte_vector)//8}d", byte_vector))

    @staticmethod
    def decode_int64s(byte_vector: bytes) -> List[int]:
        return list(struct.unpack(f"{len(byte_vector)//8}q", byte_vector))
