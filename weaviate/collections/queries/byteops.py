import struct
from typing import Generator, List


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

    @staticmethod
    def decode_strings(byte_vector: bytes) -> List[str]:
        split = byte_vector.split(b",")
        if len(split) == 1 and split[0] == b"":
            return []
        return [byte_string.decode("utf-8") for byte_string in split]

    @staticmethod
    def generate_strings(byte_vector: bytes) -> Generator[str, None, None]:
        split = byte_vector.split(b",")
        if len(split) == 1 and split[0] == b"":
            return
        for byte_string in byte_vector.split(b","):
            yield byte_string.decode("utf-8")
