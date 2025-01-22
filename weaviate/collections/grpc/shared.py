import struct
from collections.abc import Mapping
from dataclasses import dataclass
from typing import List, Optional, Sequence, Union
from typing_extensions import TypeGuard

from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.connect import ConnectionV4
from weaviate.exceptions import WeaviateInvalidInputError
from weaviate.proto.v1 import base_pb2
from weaviate.types import NUMBER
from weaviate.util import _get_vector_v4


PERMISSION_DENIED = "PERMISSION_DENIED"

UINT32_LEN = 4
UINT64_LEN = 8


class _BaseGRPC:
    def __init__(
        self,
        connection: ConnectionV4,
        consistency_level: Optional[ConsistencyLevel],
    ):
        self._connection = connection
        self._consistency_level = self._get_consistency_level(consistency_level)

    @staticmethod
    def _get_consistency_level(
        consistency_level: Optional[ConsistencyLevel],
    ) -> Optional["base_pb2.ConsistencyLevel"]:
        if consistency_level is None:
            return None

        if consistency_level.value == ConsistencyLevel.ONE:
            return base_pb2.ConsistencyLevel.CONSISTENCY_LEVEL_ONE
        elif consistency_level.value == ConsistencyLevel.QUORUM:
            return base_pb2.ConsistencyLevel.CONSISTENCY_LEVEL_QUORUM
        else:
            assert consistency_level.value == ConsistencyLevel.ALL
            return base_pb2.ConsistencyLevel.CONSISTENCY_LEVEL_ALL


class _ByteOps:
    @staticmethod
    def decode_float32s(byte_vector: bytes) -> List[float]:
        return [
            float(val) for val in struct.unpack(f"{len(byte_vector)//UINT32_LEN}f", byte_vector)
        ]

    @staticmethod
    def decode_float64s(byte_vector: bytes) -> List[float]:
        return [
            float(val) for val in struct.unpack(f"{len(byte_vector)//UINT64_LEN}d", byte_vector)
        ]

    @staticmethod
    def decode_int64s(byte_vector: bytes) -> List[int]:
        return [int(val) for val in struct.unpack(f"{len(byte_vector)//UINT64_LEN}q", byte_vector)]


@dataclass
class _Packing:
    bytes_: bytes
    type_: base_pb2.VectorType


class _Pack:
    @staticmethod
    def is_multi(
        v: Union[Sequence[NUMBER], Sequence[Sequence[NUMBER]]]
    ) -> TypeGuard[List[List[NUMBER]]]:
        return len(v) > 0 and isinstance(v[0], list)

    @staticmethod
    def is_single(
        v: Union[Sequence[NUMBER], Sequence[Sequence[NUMBER]]]
    ) -> TypeGuard[List[NUMBER]]:
        return len(v) > 0 and (isinstance(v[0], float) or isinstance(v[0], int))

    @staticmethod
    def parse_single_or_multi_vec(
        vector: Union[Sequence[NUMBER], Sequence[Sequence[NUMBER]]]
    ) -> _Packing:
        if _Pack.is_multi(vector):
            return _Packing(bytes_=_Pack.multi(vector), type_=base_pb2.VECTOR_TYPE_MULTI_FP32)
        elif _Pack.is_single(vector):
            return _Packing(bytes_=_Pack.single(vector), type_=base_pb2.VECTOR_TYPE_SINGLE_FP32)
        else:
            raise WeaviateInvalidInputError(f"Invalid vectors: {vector}")

    @staticmethod
    def vectors(
        vectors: Mapping[str, Union[Sequence[NUMBER], Sequence[Sequence[NUMBER]]]]
    ) -> List[base_pb2.Vectors]:
        return [
            base_pb2.Vectors(name=name, vector_bytes=packing.bytes_, type=packing.type_)
            for name, vec_or_vecs in vectors.items()
            if (packing := _Pack.parse_single_or_multi_vec(vec_or_vecs))
        ]

    @staticmethod
    def single(vector: Sequence[NUMBER]) -> bytes:
        vector_list = _get_vector_v4(vector)
        return struct.pack("{}f".format(len(vector_list)), *vector_list)

    @staticmethod
    def multi(vector: Sequence[Sequence[NUMBER]]) -> bytes:
        vector_list = [item for sublist in vector for item in sublist]
        return struct.pack("<H", len(vector[0])) + struct.pack(
            "{}f".format(len(vector_list)), *vector_list
        )


class _Unpack:
    @staticmethod
    def single(byte_vector: bytes) -> List[float]:
        return _ByteOps.decode_float32s(byte_vector)

    @staticmethod
    def multi(byte_vector: bytes) -> List[List[float]]:
        dim_bytes = byte_vector[:2]
        dim = int(struct.unpack("<H", dim_bytes)[0])
        byte_vector = byte_vector[2:]
        how_many = len(byte_vector) // (dim * UINT32_LEN)
        return [
            _ByteOps.decode_float32s(byte_vector[i * dim * UINT32_LEN : (i + 1) * dim * UINT32_LEN])
            for i in range(how_many)
        ]
