from weaviate.proto.v1 import base_pb2 as _base_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import (
    ClassVar as _ClassVar,
    Iterable as _Iterable,
    Mapping as _Mapping,
    Optional as _Optional,
    Union as _Union,
)

DESCRIPTOR: _descriptor.FileDescriptor

class CombinationMethod(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    COMBINATION_METHOD_UNSPECIFIED: _ClassVar[CombinationMethod]
    COMBINATION_METHOD_TYPE_SUM: _ClassVar[CombinationMethod]
    COMBINATION_METHOD_TYPE_MIN: _ClassVar[CombinationMethod]
    COMBINATION_METHOD_TYPE_AVERAGE: _ClassVar[CombinationMethod]
    COMBINATION_METHOD_TYPE_RELATIVE_SCORE: _ClassVar[CombinationMethod]
    COMBINATION_METHOD_TYPE_MANUAL: _ClassVar[CombinationMethod]

COMBINATION_METHOD_UNSPECIFIED: CombinationMethod
COMBINATION_METHOD_TYPE_SUM: CombinationMethod
COMBINATION_METHOD_TYPE_MIN: CombinationMethod
COMBINATION_METHOD_TYPE_AVERAGE: CombinationMethod
COMBINATION_METHOD_TYPE_RELATIVE_SCORE: CombinationMethod
COMBINATION_METHOD_TYPE_MANUAL: CombinationMethod

class WeightsForTarget(_message.Message):
    __slots__ = ("target", "weight")
    TARGET_FIELD_NUMBER: _ClassVar[int]
    WEIGHT_FIELD_NUMBER: _ClassVar[int]
    target: str
    weight: float
    def __init__(self, target: _Optional[str] = ..., weight: _Optional[float] = ...) -> None: ...

class Targets(_message.Message):
    __slots__ = ("target_vectors", "combination", "weights", "weights_for_targets")

    class WeightsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: float
        def __init__(self, key: _Optional[str] = ..., value: _Optional[float] = ...) -> None: ...

    TARGET_VECTORS_FIELD_NUMBER: _ClassVar[int]
    COMBINATION_FIELD_NUMBER: _ClassVar[int]
    WEIGHTS_FIELD_NUMBER: _ClassVar[int]
    WEIGHTS_FOR_TARGETS_FIELD_NUMBER: _ClassVar[int]
    target_vectors: _containers.RepeatedScalarFieldContainer[str]
    combination: CombinationMethod
    weights: _containers.ScalarMap[str, float]
    weights_for_targets: _containers.RepeatedCompositeFieldContainer[WeightsForTarget]
    def __init__(
        self,
        target_vectors: _Optional[_Iterable[str]] = ...,
        combination: _Optional[_Union[CombinationMethod, str]] = ...,
        weights: _Optional[_Mapping[str, float]] = ...,
        weights_for_targets: _Optional[_Iterable[_Union[WeightsForTarget, _Mapping]]] = ...,
    ) -> None: ...

class VectorForTarget(_message.Message):
    __slots__ = ("name", "vector_bytes", "vectors")
    NAME_FIELD_NUMBER: _ClassVar[int]
    VECTOR_BYTES_FIELD_NUMBER: _ClassVar[int]
    VECTORS_FIELD_NUMBER: _ClassVar[int]
    name: str
    vector_bytes: bytes
    vectors: _containers.RepeatedCompositeFieldContainer[_base_pb2.Vectors]
    def __init__(
        self,
        name: _Optional[str] = ...,
        vector_bytes: _Optional[bytes] = ...,
        vectors: _Optional[_Iterable[_Union[_base_pb2.Vectors, _Mapping]]] = ...,
    ) -> None: ...

class Hybrid(_message.Message):
    __slots__ = (
        "query",
        "properties",
        "vector",
        "alpha",
        "fusion_type",
        "vector_bytes",
        "target_vectors",
        "near_text",
        "near_vector",
        "targets",
        "vector_distance",
        "vectors",
    )

    class FusionType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        FUSION_TYPE_UNSPECIFIED: _ClassVar[Hybrid.FusionType]
        FUSION_TYPE_RANKED: _ClassVar[Hybrid.FusionType]
        FUSION_TYPE_RELATIVE_SCORE: _ClassVar[Hybrid.FusionType]

    FUSION_TYPE_UNSPECIFIED: Hybrid.FusionType
    FUSION_TYPE_RANKED: Hybrid.FusionType
    FUSION_TYPE_RELATIVE_SCORE: Hybrid.FusionType
    QUERY_FIELD_NUMBER: _ClassVar[int]
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    VECTOR_FIELD_NUMBER: _ClassVar[int]
    ALPHA_FIELD_NUMBER: _ClassVar[int]
    FUSION_TYPE_FIELD_NUMBER: _ClassVar[int]
    VECTOR_BYTES_FIELD_NUMBER: _ClassVar[int]
    TARGET_VECTORS_FIELD_NUMBER: _ClassVar[int]
    NEAR_TEXT_FIELD_NUMBER: _ClassVar[int]
    NEAR_VECTOR_FIELD_NUMBER: _ClassVar[int]
    TARGETS_FIELD_NUMBER: _ClassVar[int]
    VECTOR_DISTANCE_FIELD_NUMBER: _ClassVar[int]
    VECTORS_FIELD_NUMBER: _ClassVar[int]
    query: str
    properties: _containers.RepeatedScalarFieldContainer[str]
    vector: _containers.RepeatedScalarFieldContainer[float]
    alpha: float
    fusion_type: Hybrid.FusionType
    vector_bytes: bytes
    target_vectors: _containers.RepeatedScalarFieldContainer[str]
    near_text: NearTextSearch
    near_vector: NearVector
    targets: Targets
    vector_distance: float
    vectors: _containers.RepeatedCompositeFieldContainer[_base_pb2.Vectors]
    def __init__(
        self,
        query: _Optional[str] = ...,
        properties: _Optional[_Iterable[str]] = ...,
        vector: _Optional[_Iterable[float]] = ...,
        alpha: _Optional[float] = ...,
        fusion_type: _Optional[_Union[Hybrid.FusionType, str]] = ...,
        vector_bytes: _Optional[bytes] = ...,
        target_vectors: _Optional[_Iterable[str]] = ...,
        near_text: _Optional[_Union[NearTextSearch, _Mapping]] = ...,
        near_vector: _Optional[_Union[NearVector, _Mapping]] = ...,
        targets: _Optional[_Union[Targets, _Mapping]] = ...,
        vector_distance: _Optional[float] = ...,
        vectors: _Optional[_Iterable[_Union[_base_pb2.Vectors, _Mapping]]] = ...,
    ) -> None: ...

class NearVector(_message.Message):
    __slots__ = (
        "vector",
        "certainty",
        "distance",
        "vector_bytes",
        "target_vectors",
        "targets",
        "vector_per_target",
        "vector_for_targets",
        "vectors",
    )

    class VectorPerTargetEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: bytes
        def __init__(self, key: _Optional[str] = ..., value: _Optional[bytes] = ...) -> None: ...

    VECTOR_FIELD_NUMBER: _ClassVar[int]
    CERTAINTY_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    VECTOR_BYTES_FIELD_NUMBER: _ClassVar[int]
    TARGET_VECTORS_FIELD_NUMBER: _ClassVar[int]
    TARGETS_FIELD_NUMBER: _ClassVar[int]
    VECTOR_PER_TARGET_FIELD_NUMBER: _ClassVar[int]
    VECTOR_FOR_TARGETS_FIELD_NUMBER: _ClassVar[int]
    VECTORS_FIELD_NUMBER: _ClassVar[int]
    vector: _containers.RepeatedScalarFieldContainer[float]
    certainty: float
    distance: float
    vector_bytes: bytes
    target_vectors: _containers.RepeatedScalarFieldContainer[str]
    targets: Targets
    vector_per_target: _containers.ScalarMap[str, bytes]
    vector_for_targets: _containers.RepeatedCompositeFieldContainer[VectorForTarget]
    vectors: _containers.RepeatedCompositeFieldContainer[_base_pb2.Vectors]
    def __init__(
        self,
        vector: _Optional[_Iterable[float]] = ...,
        certainty: _Optional[float] = ...,
        distance: _Optional[float] = ...,
        vector_bytes: _Optional[bytes] = ...,
        target_vectors: _Optional[_Iterable[str]] = ...,
        targets: _Optional[_Union[Targets, _Mapping]] = ...,
        vector_per_target: _Optional[_Mapping[str, bytes]] = ...,
        vector_for_targets: _Optional[_Iterable[_Union[VectorForTarget, _Mapping]]] = ...,
        vectors: _Optional[_Iterable[_Union[_base_pb2.Vectors, _Mapping]]] = ...,
    ) -> None: ...

class NearObject(_message.Message):
    __slots__ = ("id", "certainty", "distance", "target_vectors", "targets")
    ID_FIELD_NUMBER: _ClassVar[int]
    CERTAINTY_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    TARGET_VECTORS_FIELD_NUMBER: _ClassVar[int]
    TARGETS_FIELD_NUMBER: _ClassVar[int]
    id: str
    certainty: float
    distance: float
    target_vectors: _containers.RepeatedScalarFieldContainer[str]
    targets: Targets
    def __init__(
        self,
        id: _Optional[str] = ...,
        certainty: _Optional[float] = ...,
        distance: _Optional[float] = ...,
        target_vectors: _Optional[_Iterable[str]] = ...,
        targets: _Optional[_Union[Targets, _Mapping]] = ...,
    ) -> None: ...

class NearTextSearch(_message.Message):
    __slots__ = (
        "query",
        "certainty",
        "distance",
        "move_to",
        "move_away",
        "target_vectors",
        "targets",
    )

    class Move(_message.Message):
        __slots__ = ("force", "concepts", "uuids")
        FORCE_FIELD_NUMBER: _ClassVar[int]
        CONCEPTS_FIELD_NUMBER: _ClassVar[int]
        UUIDS_FIELD_NUMBER: _ClassVar[int]
        force: float
        concepts: _containers.RepeatedScalarFieldContainer[str]
        uuids: _containers.RepeatedScalarFieldContainer[str]
        def __init__(
            self,
            force: _Optional[float] = ...,
            concepts: _Optional[_Iterable[str]] = ...,
            uuids: _Optional[_Iterable[str]] = ...,
        ) -> None: ...

    QUERY_FIELD_NUMBER: _ClassVar[int]
    CERTAINTY_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    MOVE_TO_FIELD_NUMBER: _ClassVar[int]
    MOVE_AWAY_FIELD_NUMBER: _ClassVar[int]
    TARGET_VECTORS_FIELD_NUMBER: _ClassVar[int]
    TARGETS_FIELD_NUMBER: _ClassVar[int]
    query: _containers.RepeatedScalarFieldContainer[str]
    certainty: float
    distance: float
    move_to: NearTextSearch.Move
    move_away: NearTextSearch.Move
    target_vectors: _containers.RepeatedScalarFieldContainer[str]
    targets: Targets
    def __init__(
        self,
        query: _Optional[_Iterable[str]] = ...,
        certainty: _Optional[float] = ...,
        distance: _Optional[float] = ...,
        move_to: _Optional[_Union[NearTextSearch.Move, _Mapping]] = ...,
        move_away: _Optional[_Union[NearTextSearch.Move, _Mapping]] = ...,
        target_vectors: _Optional[_Iterable[str]] = ...,
        targets: _Optional[_Union[Targets, _Mapping]] = ...,
    ) -> None: ...

class NearImageSearch(_message.Message):
    __slots__ = ("image", "certainty", "distance", "target_vectors", "targets")
    IMAGE_FIELD_NUMBER: _ClassVar[int]
    CERTAINTY_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    TARGET_VECTORS_FIELD_NUMBER: _ClassVar[int]
    TARGETS_FIELD_NUMBER: _ClassVar[int]
    image: str
    certainty: float
    distance: float
    target_vectors: _containers.RepeatedScalarFieldContainer[str]
    targets: Targets
    def __init__(
        self,
        image: _Optional[str] = ...,
        certainty: _Optional[float] = ...,
        distance: _Optional[float] = ...,
        target_vectors: _Optional[_Iterable[str]] = ...,
        targets: _Optional[_Union[Targets, _Mapping]] = ...,
    ) -> None: ...

class NearAudioSearch(_message.Message):
    __slots__ = ("audio", "certainty", "distance", "target_vectors", "targets")
    AUDIO_FIELD_NUMBER: _ClassVar[int]
    CERTAINTY_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    TARGET_VECTORS_FIELD_NUMBER: _ClassVar[int]
    TARGETS_FIELD_NUMBER: _ClassVar[int]
    audio: str
    certainty: float
    distance: float
    target_vectors: _containers.RepeatedScalarFieldContainer[str]
    targets: Targets
    def __init__(
        self,
        audio: _Optional[str] = ...,
        certainty: _Optional[float] = ...,
        distance: _Optional[float] = ...,
        target_vectors: _Optional[_Iterable[str]] = ...,
        targets: _Optional[_Union[Targets, _Mapping]] = ...,
    ) -> None: ...

class NearVideoSearch(_message.Message):
    __slots__ = ("video", "certainty", "distance", "target_vectors", "targets")
    VIDEO_FIELD_NUMBER: _ClassVar[int]
    CERTAINTY_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    TARGET_VECTORS_FIELD_NUMBER: _ClassVar[int]
    TARGETS_FIELD_NUMBER: _ClassVar[int]
    video: str
    certainty: float
    distance: float
    target_vectors: _containers.RepeatedScalarFieldContainer[str]
    targets: Targets
    def __init__(
        self,
        video: _Optional[str] = ...,
        certainty: _Optional[float] = ...,
        distance: _Optional[float] = ...,
        target_vectors: _Optional[_Iterable[str]] = ...,
        targets: _Optional[_Union[Targets, _Mapping]] = ...,
    ) -> None: ...

class NearDepthSearch(_message.Message):
    __slots__ = ("depth", "certainty", "distance", "target_vectors", "targets")
    DEPTH_FIELD_NUMBER: _ClassVar[int]
    CERTAINTY_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    TARGET_VECTORS_FIELD_NUMBER: _ClassVar[int]
    TARGETS_FIELD_NUMBER: _ClassVar[int]
    depth: str
    certainty: float
    distance: float
    target_vectors: _containers.RepeatedScalarFieldContainer[str]
    targets: Targets
    def __init__(
        self,
        depth: _Optional[str] = ...,
        certainty: _Optional[float] = ...,
        distance: _Optional[float] = ...,
        target_vectors: _Optional[_Iterable[str]] = ...,
        targets: _Optional[_Union[Targets, _Mapping]] = ...,
    ) -> None: ...

class NearThermalSearch(_message.Message):
    __slots__ = ("thermal", "certainty", "distance", "target_vectors", "targets")
    THERMAL_FIELD_NUMBER: _ClassVar[int]
    CERTAINTY_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    TARGET_VECTORS_FIELD_NUMBER: _ClassVar[int]
    TARGETS_FIELD_NUMBER: _ClassVar[int]
    thermal: str
    certainty: float
    distance: float
    target_vectors: _containers.RepeatedScalarFieldContainer[str]
    targets: Targets
    def __init__(
        self,
        thermal: _Optional[str] = ...,
        certainty: _Optional[float] = ...,
        distance: _Optional[float] = ...,
        target_vectors: _Optional[_Iterable[str]] = ...,
        targets: _Optional[_Union[Targets, _Mapping]] = ...,
    ) -> None: ...

class NearIMUSearch(_message.Message):
    __slots__ = ("imu", "certainty", "distance", "target_vectors", "targets")
    IMU_FIELD_NUMBER: _ClassVar[int]
    CERTAINTY_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    TARGET_VECTORS_FIELD_NUMBER: _ClassVar[int]
    TARGETS_FIELD_NUMBER: _ClassVar[int]
    imu: str
    certainty: float
    distance: float
    target_vectors: _containers.RepeatedScalarFieldContainer[str]
    targets: Targets
    def __init__(
        self,
        imu: _Optional[str] = ...,
        certainty: _Optional[float] = ...,
        distance: _Optional[float] = ...,
        target_vectors: _Optional[_Iterable[str]] = ...,
        targets: _Optional[_Union[Targets, _Mapping]] = ...,
    ) -> None: ...

class BM25(_message.Message):
    __slots__ = ("query", "properties")
    QUERY_FIELD_NUMBER: _ClassVar[int]
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    query: str
    properties: _containers.RepeatedScalarFieldContainer[str]
    def __init__(
        self, query: _Optional[str] = ..., properties: _Optional[_Iterable[str]] = ...
    ) -> None: ...
