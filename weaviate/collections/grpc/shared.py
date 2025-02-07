import struct
import uuid as uuid_lib
from typing import (
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Union,
    cast,
    Tuple,
    get_args,
)
from dataclasses import dataclass
from typing_extensions import TypeGuard

from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.grpc import (
    _ListOfVectorsQuery,
    _MultiTargetVectorJoin,
    _HybridNearText,
    _HybridNearVector,
    HybridFusion,
    HybridVectorType,
    Move,
    TargetVectorJoinType,
    NearVectorInputType,
    OneDimensionalVectorType,
    TwoDimensionalVectorType,
    PrimitiveVectorType,
)
from weaviate.connect import ConnectionV4
from weaviate.exceptions import (
    WeaviateUnsupportedFeatureError,
    WeaviateInvalidInputError,
)
from weaviate.proto.v1 import base_search_pb2, base_pb2
from weaviate.types import NUMBER, UUID
from weaviate.util import _get_vector_v4
from weaviate.validator import _is_valid, _ValidateArgument, _validate_input, _ExtraTypes


PERMISSION_DENIED = "PERMISSION_DENIED"

UINT32_LEN = 4
UINT64_LEN = 8


class _BaseGRPC:
    def __init__(
        self,
        connection: ConnectionV4,
        consistency_level: Optional[ConsistencyLevel],
        validate_arguments: bool,
    ):
        self._connection = connection
        self._consistency_level = self._get_consistency_level(consistency_level)
        self._validate_arguments = validate_arguments

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

    def _recompute_target_vector_to_grpc(
        self, target_vector: Optional[TargetVectorJoinType], target_vectors_tmp: List[str]
    ) -> Tuple[Optional[base_search_pb2.Targets], Optional[List[str]]]:
        # reorder input for targets so they match the vectors
        if isinstance(target_vector, _MultiTargetVectorJoin):
            target_vector.target_vectors = target_vectors_tmp
            if target_vector.weights is not None:
                target_vector.weights = {
                    target: target_vector.weights[target] for target in target_vectors_tmp
                }
        else:
            target_vector = target_vectors_tmp
        return self.__target_vector_to_grpc(target_vector)

    def __target_vector_to_grpc(
        self, target_vector: Optional[TargetVectorJoinType]
    ) -> Tuple[Optional[base_search_pb2.Targets], Optional[List[str]]]:
        if target_vector is None:
            return None, None

        if self._connection._weaviate_version.is_lower_than(1, 26, 0):
            if isinstance(target_vector, str):
                return None, [target_vector]
            elif isinstance(target_vector, list) and len(target_vector) == 1:
                return None, target_vector
            else:
                raise WeaviateUnsupportedFeatureError(
                    "Multiple target vectors in search",
                    str(self._connection._weaviate_version),
                    "1.26.0",
                )

        if isinstance(target_vector, str):
            return base_search_pb2.Targets(target_vectors=[target_vector]), None
        elif isinstance(target_vector, list):
            return base_search_pb2.Targets(target_vectors=target_vector), None
        else:
            return target_vector.to_grpc_target_vector(self._connection._weaviate_version), None

    def _vector_per_target(
        self,
        vector: NearVectorInputType,
        targets: Optional[base_search_pb2.Targets],
        argument_name: str,
    ) -> Tuple[Optional[Dict[str, bytes]], Optional[bytes]]:
        """@deprecated in 1.27.0, included for BC until 1.27.0 is no longer supported."""  # noqa: D401
        invalid_nv_exception = WeaviateInvalidInputError(
            f"""{argument_name} argument can be:
                                - a list of numbers
                                - a dictionary with target names as keys and lists of numbers as values
                        received: {vector}"""
        )
        if isinstance(vector, dict):
            if targets is None or len(targets.target_vectors) != len(vector):
                raise WeaviateInvalidInputError(
                    "The number of target vectors must be equal to the number of vectors."
                )

            vector_per_target: Dict[str, bytes] = {}
            for key, value in vector.items():
                nv = _get_vector_v4(value)

                if (
                    not isinstance(nv, list)
                    or len(nv) == 0
                    or not isinstance(nv[0], get_args(NUMBER))
                ):
                    raise invalid_nv_exception

                vector_per_target[key] = struct.pack("{}f".format(len(nv)), *nv)

            return vector_per_target, None
        else:
            if isinstance(vector, _ListOfVectorsQuery) or len(vector) == 0:
                raise invalid_nv_exception

            if _is_1d_vector(vector):
                near_vector = _get_vector_v4(vector)
                if not isinstance(near_vector, list):
                    raise invalid_nv_exception
                return None, struct.pack("{}f".format(len(near_vector)), *near_vector)
            else:
                raise WeaviateInvalidInputError(
                    """Providing lists of lists has been deprecated. Please provide a dictionary with target names as
                    keys and lists of numbers as values."""
                )

    def _vector_for_target(
        self,
        vector: NearVectorInputType,
        targets: Optional[base_search_pb2.Targets],
        argument_name: str,
    ) -> Tuple[
        Optional[List[base_search_pb2.VectorForTarget]], Optional[bytes], Optional[List[str]]
    ]:
        invalid_nv_exception = WeaviateInvalidInputError(
            f"""{argument_name} argument can be:
                                - a list of numbers
                                - a dictionary with target names as keys and lists of numbers as values for multi target search. The keys must match the given target vectors
                        received: {vector} and {targets}."""
        )

        vector_for_target: List[base_search_pb2.VectorForTarget] = []
        target_vectors: List[str] = []

        def add_1d_vector(val: OneDimensionalVectorType, key: str) -> None:
            vec = _get_vector_v4(val)

            if (
                not isinstance(vec, list)
                or len(vec) == 0
                or not isinstance(vec[0], get_args(NUMBER))
            ):
                raise invalid_nv_exception

            if self._connection._weaviate_version.is_lower_than(1, 29, 0):
                vector_for_target.append(
                    base_search_pb2.VectorForTarget(name=key, vector_bytes=_Pack.single(vec))
                )
            else:
                vector_for_target.append(
                    base_search_pb2.VectorForTarget(
                        name=key,
                        vectors=[
                            base_pb2.Vectors(
                                name=key,
                                vector_bytes=_Pack.single(vec),
                                type=base_pb2.Vectors.VECTOR_TYPE_SINGLE_FP32,
                            )
                        ],
                    )
                )
            target_vectors.append(key)

        def add_2d_vector(value: TwoDimensionalVectorType, key: str) -> None:
            if self._connection._weaviate_version.is_lower_than(1, 29, 0):
                for v in value:
                    add_1d_vector(v, key)
                return
            vector_for_target.append(
                base_search_pb2.VectorForTarget(
                    name=key,
                    vectors=[
                        base_pb2.Vectors(
                            name=key,
                            vector_bytes=_Pack.multi([_get_vector_v4(v) for v in value]),
                            type=base_pb2.Vectors.VECTOR_TYPE_MULTI_FP32,
                        )
                    ],
                )
            )
            target_vectors.append(key)

        def add_list_of_vectors(value: _ListOfVectorsQuery, key: str) -> None:
            if _ListOfVectorsQuery.is_one_dimensional(
                value
            ) and self._connection._weaviate_version.is_lower_than(1, 29, 0):
                for v in value.vectors:
                    add_1d_vector(v, key)
                return
            elif _ListOfVectorsQuery.is_one_dimensional(
                value
            ) and self._connection._weaviate_version.is_at_least(1, 29, 0):
                vectors = [
                    base_pb2.Vectors(
                        name=key,
                        vector_bytes=_Pack.multi([_get_vector_v4(v) for v in value.vectors]),
                        type=base_pb2.Vectors.VECTOR_TYPE_MULTI_FP32,
                    )
                ]
            elif _ListOfVectorsQuery.is_two_dimensional(value):
                vectors = [
                    base_pb2.Vectors(
                        name=key,
                        vector_bytes=_Pack.multi([_get_vector_v4(v) for v in vecs]),
                        type=base_pb2.Vectors.VECTOR_TYPE_MULTI_FP32,
                    )
                    for vecs in value.vectors
                ]
            else:
                raise WeaviateInvalidInputError(f"Invalid list of vectors: {value}")
            vector_for_target.append(
                base_search_pb2.VectorForTarget(
                    name=key,
                    vectors=vectors,
                )
            )
            target_vectors.append(key)

        if isinstance(vector, dict):
            if (
                len(vector) == 0
                or targets is None
                or len(set(targets.target_vectors)) != len(vector)
            ):
                raise invalid_nv_exception
            for key, value in vector.items():
                if _is_1d_vector(value):
                    add_1d_vector(value, key)
                elif _is_2d_vector(value):
                    add_2d_vector(value, key)
                elif isinstance(value, _ListOfVectorsQuery):
                    add_list_of_vectors(value, key)
                else:
                    raise invalid_nv_exception
            return vector_for_target, None, target_vectors
        else:
            if _is_1d_vector(vector):
                near_vector = _get_vector_v4(vector)
                if not isinstance(near_vector, list):
                    raise invalid_nv_exception
                return None, struct.pack("{}f".format(len(near_vector)), *near_vector), None
            else:
                raise WeaviateInvalidInputError(
                    """Providing lists of lists has been deprecated. Please provide a dictionary with target names as
                    keys and lists of numbers as values."""
                )

    def _parse_near_options(
        self,
        certainty: Optional[NUMBER] = None,
        distance: Optional[NUMBER] = None,
    ) -> Tuple[Optional[float], Optional[float]]:
        if self._validate_arguments:
            _validate_input(
                [
                    _ValidateArgument([float, int, None], "certainty", certainty),
                    _ValidateArgument([float, int, None], "distance", distance),
                ]
            )
        return (
            float(certainty) if certainty is not None else None,
            float(distance) if distance is not None else None,
        )

    def _parse_near_vector(
        self,
        near_vector: NearVectorInputType,
        certainty: Optional[NUMBER],
        distance: Optional[NUMBER],
        target_vector: Optional[TargetVectorJoinType],
    ) -> base_search_pb2.NearVector:
        if self._validate_arguments:
            _validate_input(
                [
                    _ValidateArgument(
                        [
                            List,
                            Dict,
                            _ExtraTypes.PANDAS,
                            _ExtraTypes.POLARS,
                            _ExtraTypes.NUMPY,
                            _ExtraTypes.TF,
                        ],
                        "near_vector",
                        near_vector,
                    ),
                    _ValidateArgument(
                        [str, None, List, _MultiTargetVectorJoin], "target_vector", target_vector
                    ),
                ]
            )

        certainty, distance = self._parse_near_options(certainty, distance)

        targets, target_vectors = self.__target_vector_to_grpc(target_vector)

        if _is_1d_vector(near_vector) and len(near_vector) > 0:
            # fast path for simple single-vector
            if self._connection._weaviate_version.is_lower_than(1, 29, 0):
                near_vector_grpc: Optional[bytes] = struct.pack(
                    "{}f".format(len(near_vector)), *near_vector
                )
                vector_per_target_tmp = None
                vector_for_targets = None
                vectors = None
            else:
                near_vector_grpc = None
                vector_per_target_tmp = None
                vector_for_targets = None
                vectors = [
                    base_pb2.Vectors(
                        vector_bytes=_Pack.single(near_vector),
                        type=base_pb2.Vectors.VECTOR_TYPE_SINGLE_FP32,
                    )
                ]
        elif _is_2d_vector(near_vector) and self._connection._weaviate_version.is_at_least(
            1, 29, 0
        ):
            # fast path for simple multi-vector
            near_vector_grpc = None
            vector_per_target_tmp = None
            vector_for_targets = None
            vectors = [
                base_pb2.Vectors(
                    vector_bytes=_Pack.multi(near_vector),
                    type=base_pb2.Vectors.VECTOR_TYPE_MULTI_FP32,
                )
            ]
        else:
            if self._connection._weaviate_version.is_lower_than(1, 27, 0):
                vector_per_target_tmp, near_vector_grpc = self._vector_per_target(
                    near_vector, targets, "near_vector"
                )
                vector_for_targets = None
            else:
                vector_for_targets, near_vector_grpc, target_vectors_tmp = self._vector_for_target(
                    near_vector, targets, "near_vector"
                )
                vector_per_target_tmp = None
                if target_vectors_tmp is not None:
                    targets, target_vectors = self._recompute_target_vector_to_grpc(
                        target_vector, target_vectors_tmp
                    )
            vectors = None
        return base_search_pb2.NearVector(
            vector_bytes=near_vector_grpc,
            certainty=certainty,
            distance=distance,
            targets=targets,
            target_vectors=target_vectors,
            vector_per_target=vector_per_target_tmp,
            vector_for_targets=vector_for_targets,
            vectors=vectors,
        )

    @staticmethod
    def __parse_move(move: Optional[Move]) -> Optional[base_search_pb2.NearTextSearch.Move]:
        return (
            base_search_pb2.NearTextSearch.Move(
                force=move.force,
                concepts=move._concepts_list,
                uuids=move._objects_list,
            )
            if move is not None
            else None
        )

    def _parse_near_text(
        self,
        near_text: Union[List[str], str],
        certainty: Optional[NUMBER],
        distance: Optional[NUMBER],
        move_to: Optional[Move],
        move_away: Optional[Move],
        target_vector: Optional[TargetVectorJoinType],
    ) -> base_search_pb2.NearTextSearch:
        if self._validate_arguments:
            _validate_input(
                [
                    _ValidateArgument([List, str], "near_text", near_text),
                    _ValidateArgument([Move, None], "move_away", move_away),
                    _ValidateArgument([Move, None], "move_to", move_to),
                    _ValidateArgument(
                        [str, List, _MultiTargetVectorJoin, None], "target_vector", target_vector
                    ),
                ]
            )

        if isinstance(near_text, str):
            near_text = [near_text]
        certainty, distance = self._parse_near_options(certainty, distance)
        targets, target_vector = self.__target_vector_to_grpc(target_vector)

        return base_search_pb2.NearTextSearch(
            query=near_text,
            certainty=certainty,
            distance=distance,
            move_away=self.__parse_move(move_away),
            move_to=self.__parse_move(move_to),
            targets=targets,
            target_vectors=target_vector,
        )

    def _parse_near_object(
        self,
        near_object: UUID,
        certainty: Optional[NUMBER],
        distance: Optional[NUMBER],
        target_vector: Optional[TargetVectorJoinType],
    ) -> base_search_pb2.NearObject:
        if self._validate_arguments:
            _validate_input(
                [
                    _ValidateArgument([str, uuid_lib.UUID], "near_object", near_object),
                    _ValidateArgument(
                        [str, None, List, _MultiTargetVectorJoin], "target_vector", target_vector
                    ),
                ]
            )

        certainty, distance = self._parse_near_options(certainty, distance)

        targets, target_vector = self.__target_vector_to_grpc(target_vector)

        return base_search_pb2.NearObject(
            id=str(near_object),
            certainty=certainty,
            distance=distance,
            targets=targets,
            target_vectors=target_vector,
        )

    def _parse_media(
        self,
        media: str,
        type_: Literal["audio", "depth", "image", "imu", "thermal", "video"],
        certainty: Optional[NUMBER],
        distance: Optional[NUMBER],
        target_vector: Optional[TargetVectorJoinType],
    ) -> dict:
        if self._validate_arguments:
            _validate_input(
                [
                    _ValidateArgument([str], "media", media),
                    _ValidateArgument(
                        [str, None, List, _MultiTargetVectorJoin], "target_vector", target_vector
                    ),
                ]
            )

        certainty, distance = self._parse_near_options(certainty, distance)

        kwargs: Dict[str, Any] = {}
        targets, target_vector = self.__target_vector_to_grpc(target_vector)
        if type_ == "audio":
            kwargs["near_audio"] = base_search_pb2.NearAudioSearch(
                audio=media,
                distance=distance,
                certainty=certainty,
                target_vectors=target_vector,
                targets=targets,
            )
        elif type_ == "depth":
            kwargs["near_depth"] = base_search_pb2.NearDepthSearch(
                depth=media,
                distance=distance,
                certainty=certainty,
                target_vectors=target_vector,
                targets=targets,
            )
        elif type_ == "image":
            kwargs["near_image"] = base_search_pb2.NearImageSearch(
                image=media,
                distance=distance,
                certainty=certainty,
                target_vectors=target_vector,
                targets=targets,
            )
        elif type_ == "imu":
            kwargs["near_imu"] = base_search_pb2.NearIMUSearch(
                imu=media,
                distance=distance,
                certainty=certainty,
                target_vectors=target_vector,
                targets=targets,
            )
        elif type_ == "thermal":
            kwargs["near_thermal"] = base_search_pb2.NearThermalSearch(
                thermal=media,
                distance=distance,
                certainty=certainty,
                target_vectors=target_vector,
                targets=targets,
            )
        elif type_ == "video":
            kwargs["near_video"] = base_search_pb2.NearVideoSearch(
                video=media,
                distance=distance,
                certainty=certainty,
                target_vectors=target_vector,
                targets=targets,
            )
        else:
            raise ValueError(
                f"type_ must be one of ['audio', 'depth', 'image', 'imu', 'thermal', 'video'], but got {type_}"
            )
        return kwargs

    def _parse_hybrid(
        self,
        query: Optional[str],
        alpha: Optional[float],
        vector: Optional[HybridVectorType],
        properties: Optional[List[str]],
        fusion_type: Optional[HybridFusion],
        distance: Optional[NUMBER],
        target_vector: Optional[TargetVectorJoinType],
    ) -> Union[base_search_pb2.Hybrid, None]:
        if self._connection._weaviate_version.is_lower_than(1, 25, 0) and (
            isinstance(vector, _HybridNearText) or isinstance(vector, _HybridNearVector)
        ):
            raise WeaviateUnsupportedFeatureError(
                "Hybrid search with NearText or NearVector",
                str(self._connection._weaviate_version),
                "1.25.0",
            )
        if self._validate_arguments:
            _validate_input(
                [
                    _ValidateArgument([None, str], "query", query),
                    _ValidateArgument([float, int, None], "alpha", alpha),
                    _ValidateArgument(
                        [
                            List,
                            Dict,
                            _ExtraTypes.PANDAS,
                            _ExtraTypes.POLARS,
                            _ExtraTypes.NUMPY,
                            _ExtraTypes.TF,
                            _HybridNearText,
                            _HybridNearVector,
                            None,
                        ],
                        "vector",
                        vector,
                    ),
                    _ValidateArgument([List, None], "properties", properties),
                    _ValidateArgument([HybridFusion, None], "fusion_type", fusion_type),
                    _ValidateArgument(
                        [str, None, List, _MultiTargetVectorJoin], "target_vector", target_vector
                    ),
                ]
            )

        # Set hybrid search to only query the other search-type if one of the two is not set
        if query is None:
            alpha = 1

        targets, target_vectors = self.__target_vector_to_grpc(target_vector)

        near_text, near_vector, vector_bytes = None, None, None

        if vector is None:
            pass
        elif isinstance(vector, list) and len(vector) > 0 and isinstance(vector[0], float):
            # fast path for simple vector
            vector_bytes = struct.pack("{}f".format(len(vector)), *vector)
        elif isinstance(vector, _HybridNearText):
            near_text = base_search_pb2.NearTextSearch(
                query=[vector.text] if isinstance(vector.text, str) else vector.text,
                certainty=vector.certainty,
                distance=vector.distance,
                move_away=self.__parse_move(vector.move_away),
                move_to=self.__parse_move(vector.move_to),
            )
        elif isinstance(vector, _HybridNearVector):
            if self._connection._weaviate_version.is_lower_than(1, 27, 0):
                vector_per_target_tmp, vector_bytes_tmp = self._vector_per_target(
                    vector.vector, targets, "vector"
                )
                vector_for_targets_tmp = None
            else:
                (
                    vector_for_targets_tmp,
                    vector_bytes_tmp,
                    target_vectors_tmp,
                ) = self._vector_for_target(vector.vector, targets, "vector")
                vector_per_target_tmp = None
                if target_vectors_tmp is not None:
                    targets, target_vectors = self._recompute_target_vector_to_grpc(
                        target_vector, target_vectors_tmp
                    )

            near_vector = base_search_pb2.NearVector(
                vector_bytes=vector_bytes_tmp,
                certainty=vector.certainty,
                distance=vector.distance,
                vector_per_target=vector_per_target_tmp,
                vector_for_targets=vector_for_targets_tmp,
            )
        else:
            if self._connection._weaviate_version.is_lower_than(1, 27, 0):
                vector_per_target_tmp, vector_bytes_tmp = self._vector_per_target(
                    vector, targets, "vector"
                )
                vector_for_targets_tmp = None
            else:
                (
                    vector_for_targets_tmp,
                    vector_bytes_tmp,
                    target_vectors_tmp,
                ) = self._vector_for_target(vector, targets, "vector")
                vector_per_target_tmp = None
                if target_vectors_tmp is not None:
                    targets, target_vectors = self._recompute_target_vector_to_grpc(
                        target_vector, target_vectors_tmp
                    )
                else:
                    targets, target_vectors = self.__target_vector_to_grpc(target_vector)

            if vector_per_target_tmp is not None or vector_for_targets_tmp is not None:
                near_vector = base_search_pb2.NearVector(
                    vector_bytes=vector_bytes_tmp,
                    vector_per_target=vector_per_target_tmp,
                    vector_for_targets=vector_for_targets_tmp,
                )
            else:
                vector_bytes = vector_bytes_tmp

        return (
            base_search_pb2.Hybrid(
                properties=properties,
                query=query,
                alpha=float(alpha) if alpha is not None else None,
                fusion_type=(
                    cast(
                        base_search_pb2.Hybrid.FusionType,
                        base_search_pb2.Hybrid.FusionType.Value(fusion_type.value),
                    )
                    if fusion_type is not None
                    else None
                ),
                target_vectors=target_vectors,
                targets=targets,
                near_text=near_text,
                near_vector=near_vector,
                vector_bytes=vector_bytes,
                vector_distance=distance,
            )
            if query is not None or vector is not None
            else None
        )


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
    type_: base_pb2.Vectors.VectorType


class _Pack:
    @staticmethod
    def parse_single_or_multi_vec(vector: PrimitiveVectorType) -> _Packing:
        if _is_2d_vector(vector):
            return _Packing(
                bytes_=_Pack.multi(vector), type_=base_pb2.Vectors.VECTOR_TYPE_MULTI_FP32
            )
        elif _is_1d_vector(vector):
            return _Packing(
                bytes_=_Pack.single(vector), type_=base_pb2.Vectors.VECTOR_TYPE_SINGLE_FP32
            )
        else:
            raise WeaviateInvalidInputError(f"Invalid vectors: {vector}")

    @staticmethod
    def single(vector: OneDimensionalVectorType) -> bytes:
        vector_list = _get_vector_v4(vector)
        return struct.pack("{}f".format(len(vector_list)), *vector_list)

    @staticmethod
    def multi(vector: TwoDimensionalVectorType) -> bytes:
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


def _is_1d_vector(inputs: Any) -> TypeGuard[OneDimensionalVectorType]:
    try:
        if len(inputs) == 0:
            return False
    except TypeError:
        return False
    if __is_list_type(inputs):
        return not __is_list_type(inputs[0])
    return False


def _is_2d_vector(inputs: Any) -> TypeGuard[TwoDimensionalVectorType]:
    try:
        if len(inputs) == 0:
            return False
    except TypeError:
        return False
    if __is_list_type(inputs):
        return _is_1d_vector(inputs[0])
    return False


def __is_list_type(inputs: Any) -> bool:
    try:
        if len(inputs) == 0:
            return False
    except TypeError:
        return False

    return any(
        _is_valid(types, inputs)
        for types in [
            List,
            _ExtraTypes.TF,
            _ExtraTypes.PANDAS,
            _ExtraTypes.NUMPY,
            _ExtraTypes.POLARS,
        ]
    )
