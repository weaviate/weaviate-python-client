from google.protobuf import struct_pb2 as _struct_pb2
from weaviate.proto.v1 import base_pb2 as _base_pb2
from weaviate.proto.v1 import base_search_pb2 as _base_search_pb2
from weaviate.proto.v1 import generative_pb2 as _generative_pb2
from weaviate.proto.v1 import properties_pb2 as _properties_pb2
from google.protobuf.internal import containers as _containers
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

class SearchRequest(_message.Message):
    __slots__ = (
        "collection",
        "tenant",
        "consistency_level",
        "properties",
        "metadata",
        "group_by",
        "limit",
        "offset",
        "autocut",
        "after",
        "sort_by",
        "filters",
        "hybrid_search",
        "bm25_search",
        "near_vector",
        "near_object",
        "near_text",
        "near_image",
        "near_audio",
        "near_video",
        "near_depth",
        "near_thermal",
        "near_imu",
        "generative",
        "rerank",
        "uses_123_api",
        "uses_125_api",
        "uses_127_api",
    )
    COLLECTION_FIELD_NUMBER: _ClassVar[int]
    TENANT_FIELD_NUMBER: _ClassVar[int]
    CONSISTENCY_LEVEL_FIELD_NUMBER: _ClassVar[int]
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    GROUP_BY_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    OFFSET_FIELD_NUMBER: _ClassVar[int]
    AUTOCUT_FIELD_NUMBER: _ClassVar[int]
    AFTER_FIELD_NUMBER: _ClassVar[int]
    SORT_BY_FIELD_NUMBER: _ClassVar[int]
    FILTERS_FIELD_NUMBER: _ClassVar[int]
    HYBRID_SEARCH_FIELD_NUMBER: _ClassVar[int]
    BM25_SEARCH_FIELD_NUMBER: _ClassVar[int]
    NEAR_VECTOR_FIELD_NUMBER: _ClassVar[int]
    NEAR_OBJECT_FIELD_NUMBER: _ClassVar[int]
    NEAR_TEXT_FIELD_NUMBER: _ClassVar[int]
    NEAR_IMAGE_FIELD_NUMBER: _ClassVar[int]
    NEAR_AUDIO_FIELD_NUMBER: _ClassVar[int]
    NEAR_VIDEO_FIELD_NUMBER: _ClassVar[int]
    NEAR_DEPTH_FIELD_NUMBER: _ClassVar[int]
    NEAR_THERMAL_FIELD_NUMBER: _ClassVar[int]
    NEAR_IMU_FIELD_NUMBER: _ClassVar[int]
    GENERATIVE_FIELD_NUMBER: _ClassVar[int]
    RERANK_FIELD_NUMBER: _ClassVar[int]
    USES_123_API_FIELD_NUMBER: _ClassVar[int]
    USES_125_API_FIELD_NUMBER: _ClassVar[int]
    USES_127_API_FIELD_NUMBER: _ClassVar[int]
    collection: str
    tenant: str
    consistency_level: _base_pb2.ConsistencyLevel
    properties: PropertiesRequest
    metadata: MetadataRequest
    group_by: GroupBy
    limit: int
    offset: int
    autocut: int
    after: str
    sort_by: _containers.RepeatedCompositeFieldContainer[SortBy]
    filters: _base_pb2.Filters
    hybrid_search: _base_search_pb2.Hybrid
    bm25_search: _base_search_pb2.BM25
    near_vector: _base_search_pb2.NearVector
    near_object: _base_search_pb2.NearObject
    near_text: _base_search_pb2.NearTextSearch
    near_image: _base_search_pb2.NearImageSearch
    near_audio: _base_search_pb2.NearAudioSearch
    near_video: _base_search_pb2.NearVideoSearch
    near_depth: _base_search_pb2.NearDepthSearch
    near_thermal: _base_search_pb2.NearThermalSearch
    near_imu: _base_search_pb2.NearIMUSearch
    generative: _generative_pb2.GenerativeSearch
    rerank: Rerank
    uses_123_api: bool
    uses_125_api: bool
    uses_127_api: bool
    def __init__(
        self,
        collection: _Optional[str] = ...,
        tenant: _Optional[str] = ...,
        consistency_level: _Optional[_Union[_base_pb2.ConsistencyLevel, str]] = ...,
        properties: _Optional[_Union[PropertiesRequest, _Mapping]] = ...,
        metadata: _Optional[_Union[MetadataRequest, _Mapping]] = ...,
        group_by: _Optional[_Union[GroupBy, _Mapping]] = ...,
        limit: _Optional[int] = ...,
        offset: _Optional[int] = ...,
        autocut: _Optional[int] = ...,
        after: _Optional[str] = ...,
        sort_by: _Optional[_Iterable[_Union[SortBy, _Mapping]]] = ...,
        filters: _Optional[_Union[_base_pb2.Filters, _Mapping]] = ...,
        hybrid_search: _Optional[_Union[_base_search_pb2.Hybrid, _Mapping]] = ...,
        bm25_search: _Optional[_Union[_base_search_pb2.BM25, _Mapping]] = ...,
        near_vector: _Optional[_Union[_base_search_pb2.NearVector, _Mapping]] = ...,
        near_object: _Optional[_Union[_base_search_pb2.NearObject, _Mapping]] = ...,
        near_text: _Optional[_Union[_base_search_pb2.NearTextSearch, _Mapping]] = ...,
        near_image: _Optional[_Union[_base_search_pb2.NearImageSearch, _Mapping]] = ...,
        near_audio: _Optional[_Union[_base_search_pb2.NearAudioSearch, _Mapping]] = ...,
        near_video: _Optional[_Union[_base_search_pb2.NearVideoSearch, _Mapping]] = ...,
        near_depth: _Optional[_Union[_base_search_pb2.NearDepthSearch, _Mapping]] = ...,
        near_thermal: _Optional[_Union[_base_search_pb2.NearThermalSearch, _Mapping]] = ...,
        near_imu: _Optional[_Union[_base_search_pb2.NearIMUSearch, _Mapping]] = ...,
        generative: _Optional[_Union[_generative_pb2.GenerativeSearch, _Mapping]] = ...,
        rerank: _Optional[_Union[Rerank, _Mapping]] = ...,
        uses_123_api: bool = ...,
        uses_125_api: bool = ...,
        uses_127_api: bool = ...,
    ) -> None: ...

class GroupBy(_message.Message):
    __slots__ = ("path", "number_of_groups", "objects_per_group")
    PATH_FIELD_NUMBER: _ClassVar[int]
    NUMBER_OF_GROUPS_FIELD_NUMBER: _ClassVar[int]
    OBJECTS_PER_GROUP_FIELD_NUMBER: _ClassVar[int]
    path: _containers.RepeatedScalarFieldContainer[str]
    number_of_groups: int
    objects_per_group: int
    def __init__(
        self,
        path: _Optional[_Iterable[str]] = ...,
        number_of_groups: _Optional[int] = ...,
        objects_per_group: _Optional[int] = ...,
    ) -> None: ...

class SortBy(_message.Message):
    __slots__ = ("ascending", "path")
    ASCENDING_FIELD_NUMBER: _ClassVar[int]
    PATH_FIELD_NUMBER: _ClassVar[int]
    ascending: bool
    path: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, ascending: bool = ..., path: _Optional[_Iterable[str]] = ...) -> None: ...

class MetadataRequest(_message.Message):
    __slots__ = (
        "uuid",
        "vector",
        "creation_time_unix",
        "last_update_time_unix",
        "distance",
        "certainty",
        "score",
        "explain_score",
        "is_consistent",
        "vectors",
    )
    UUID_FIELD_NUMBER: _ClassVar[int]
    VECTOR_FIELD_NUMBER: _ClassVar[int]
    CREATION_TIME_UNIX_FIELD_NUMBER: _ClassVar[int]
    LAST_UPDATE_TIME_UNIX_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    CERTAINTY_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    EXPLAIN_SCORE_FIELD_NUMBER: _ClassVar[int]
    IS_CONSISTENT_FIELD_NUMBER: _ClassVar[int]
    VECTORS_FIELD_NUMBER: _ClassVar[int]
    uuid: bool
    vector: bool
    creation_time_unix: bool
    last_update_time_unix: bool
    distance: bool
    certainty: bool
    score: bool
    explain_score: bool
    is_consistent: bool
    vectors: _containers.RepeatedScalarFieldContainer[str]
    def __init__(
        self,
        uuid: bool = ...,
        vector: bool = ...,
        creation_time_unix: bool = ...,
        last_update_time_unix: bool = ...,
        distance: bool = ...,
        certainty: bool = ...,
        score: bool = ...,
        explain_score: bool = ...,
        is_consistent: bool = ...,
        vectors: _Optional[_Iterable[str]] = ...,
    ) -> None: ...

class PropertiesRequest(_message.Message):
    __slots__ = (
        "non_ref_properties",
        "ref_properties",
        "object_properties",
        "return_all_nonref_properties",
    )
    NON_REF_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    REF_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    OBJECT_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    RETURN_ALL_NONREF_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    non_ref_properties: _containers.RepeatedScalarFieldContainer[str]
    ref_properties: _containers.RepeatedCompositeFieldContainer[RefPropertiesRequest]
    object_properties: _containers.RepeatedCompositeFieldContainer[ObjectPropertiesRequest]
    return_all_nonref_properties: bool
    def __init__(
        self,
        non_ref_properties: _Optional[_Iterable[str]] = ...,
        ref_properties: _Optional[_Iterable[_Union[RefPropertiesRequest, _Mapping]]] = ...,
        object_properties: _Optional[_Iterable[_Union[ObjectPropertiesRequest, _Mapping]]] = ...,
        return_all_nonref_properties: bool = ...,
    ) -> None: ...

class ObjectPropertiesRequest(_message.Message):
    __slots__ = ("prop_name", "primitive_properties", "object_properties")
    PROP_NAME_FIELD_NUMBER: _ClassVar[int]
    PRIMITIVE_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    OBJECT_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    prop_name: str
    primitive_properties: _containers.RepeatedScalarFieldContainer[str]
    object_properties: _containers.RepeatedCompositeFieldContainer[ObjectPropertiesRequest]
    def __init__(
        self,
        prop_name: _Optional[str] = ...,
        primitive_properties: _Optional[_Iterable[str]] = ...,
        object_properties: _Optional[_Iterable[_Union[ObjectPropertiesRequest, _Mapping]]] = ...,
    ) -> None: ...

class RefPropertiesRequest(_message.Message):
    __slots__ = ("reference_property", "properties", "metadata", "target_collection")
    REFERENCE_PROPERTY_FIELD_NUMBER: _ClassVar[int]
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    TARGET_COLLECTION_FIELD_NUMBER: _ClassVar[int]
    reference_property: str
    properties: PropertiesRequest
    metadata: MetadataRequest
    target_collection: str
    def __init__(
        self,
        reference_property: _Optional[str] = ...,
        properties: _Optional[_Union[PropertiesRequest, _Mapping]] = ...,
        metadata: _Optional[_Union[MetadataRequest, _Mapping]] = ...,
        target_collection: _Optional[str] = ...,
    ) -> None: ...

class Rerank(_message.Message):
    __slots__ = ("property", "query")
    PROPERTY_FIELD_NUMBER: _ClassVar[int]
    QUERY_FIELD_NUMBER: _ClassVar[int]
    property: str
    query: str
    def __init__(self, property: _Optional[str] = ..., query: _Optional[str] = ...) -> None: ...

class SearchReply(_message.Message):
    __slots__ = (
        "took",
        "results",
        "generative_grouped_result",
        "group_by_results",
        "generative_grouped_results",
    )
    TOOK_FIELD_NUMBER: _ClassVar[int]
    RESULTS_FIELD_NUMBER: _ClassVar[int]
    GENERATIVE_GROUPED_RESULT_FIELD_NUMBER: _ClassVar[int]
    GROUP_BY_RESULTS_FIELD_NUMBER: _ClassVar[int]
    GENERATIVE_GROUPED_RESULTS_FIELD_NUMBER: _ClassVar[int]
    took: float
    results: _containers.RepeatedCompositeFieldContainer[SearchResult]
    generative_grouped_result: str
    group_by_results: _containers.RepeatedCompositeFieldContainer[GroupByResult]
    generative_grouped_results: _generative_pb2.GenerativeResult
    def __init__(
        self,
        took: _Optional[float] = ...,
        results: _Optional[_Iterable[_Union[SearchResult, _Mapping]]] = ...,
        generative_grouped_result: _Optional[str] = ...,
        group_by_results: _Optional[_Iterable[_Union[GroupByResult, _Mapping]]] = ...,
        generative_grouped_results: _Optional[
            _Union[_generative_pb2.GenerativeResult, _Mapping]
        ] = ...,
    ) -> None: ...

class RerankReply(_message.Message):
    __slots__ = ("score",)
    SCORE_FIELD_NUMBER: _ClassVar[int]
    score: float
    def __init__(self, score: _Optional[float] = ...) -> None: ...

class GroupByResult(_message.Message):
    __slots__ = (
        "name",
        "min_distance",
        "max_distance",
        "number_of_objects",
        "objects",
        "rerank",
        "generative",
        "generative_result",
    )
    NAME_FIELD_NUMBER: _ClassVar[int]
    MIN_DISTANCE_FIELD_NUMBER: _ClassVar[int]
    MAX_DISTANCE_FIELD_NUMBER: _ClassVar[int]
    NUMBER_OF_OBJECTS_FIELD_NUMBER: _ClassVar[int]
    OBJECTS_FIELD_NUMBER: _ClassVar[int]
    RERANK_FIELD_NUMBER: _ClassVar[int]
    GENERATIVE_FIELD_NUMBER: _ClassVar[int]
    GENERATIVE_RESULT_FIELD_NUMBER: _ClassVar[int]
    name: str
    min_distance: float
    max_distance: float
    number_of_objects: int
    objects: _containers.RepeatedCompositeFieldContainer[SearchResult]
    rerank: RerankReply
    generative: _generative_pb2.GenerativeReply
    generative_result: _generative_pb2.GenerativeResult
    def __init__(
        self,
        name: _Optional[str] = ...,
        min_distance: _Optional[float] = ...,
        max_distance: _Optional[float] = ...,
        number_of_objects: _Optional[int] = ...,
        objects: _Optional[_Iterable[_Union[SearchResult, _Mapping]]] = ...,
        rerank: _Optional[_Union[RerankReply, _Mapping]] = ...,
        generative: _Optional[_Union[_generative_pb2.GenerativeReply, _Mapping]] = ...,
        generative_result: _Optional[_Union[_generative_pb2.GenerativeResult, _Mapping]] = ...,
    ) -> None: ...

class SearchResult(_message.Message):
    __slots__ = ("properties", "metadata", "generative")
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    GENERATIVE_FIELD_NUMBER: _ClassVar[int]
    properties: PropertiesResult
    metadata: MetadataResult
    generative: _generative_pb2.GenerativeResult
    def __init__(
        self,
        properties: _Optional[_Union[PropertiesResult, _Mapping]] = ...,
        metadata: _Optional[_Union[MetadataResult, _Mapping]] = ...,
        generative: _Optional[_Union[_generative_pb2.GenerativeResult, _Mapping]] = ...,
    ) -> None: ...

class MetadataResult(_message.Message):
    __slots__ = (
        "id",
        "vector",
        "creation_time_unix",
        "creation_time_unix_present",
        "last_update_time_unix",
        "last_update_time_unix_present",
        "distance",
        "distance_present",
        "certainty",
        "certainty_present",
        "score",
        "score_present",
        "explain_score",
        "explain_score_present",
        "is_consistent",
        "generative",
        "generative_present",
        "is_consistent_present",
        "vector_bytes",
        "id_as_bytes",
        "rerank_score",
        "rerank_score_present",
        "vectors",
    )
    ID_FIELD_NUMBER: _ClassVar[int]
    VECTOR_FIELD_NUMBER: _ClassVar[int]
    CREATION_TIME_UNIX_FIELD_NUMBER: _ClassVar[int]
    CREATION_TIME_UNIX_PRESENT_FIELD_NUMBER: _ClassVar[int]
    LAST_UPDATE_TIME_UNIX_FIELD_NUMBER: _ClassVar[int]
    LAST_UPDATE_TIME_UNIX_PRESENT_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_PRESENT_FIELD_NUMBER: _ClassVar[int]
    CERTAINTY_FIELD_NUMBER: _ClassVar[int]
    CERTAINTY_PRESENT_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    SCORE_PRESENT_FIELD_NUMBER: _ClassVar[int]
    EXPLAIN_SCORE_FIELD_NUMBER: _ClassVar[int]
    EXPLAIN_SCORE_PRESENT_FIELD_NUMBER: _ClassVar[int]
    IS_CONSISTENT_FIELD_NUMBER: _ClassVar[int]
    GENERATIVE_FIELD_NUMBER: _ClassVar[int]
    GENERATIVE_PRESENT_FIELD_NUMBER: _ClassVar[int]
    IS_CONSISTENT_PRESENT_FIELD_NUMBER: _ClassVar[int]
    VECTOR_BYTES_FIELD_NUMBER: _ClassVar[int]
    ID_AS_BYTES_FIELD_NUMBER: _ClassVar[int]
    RERANK_SCORE_FIELD_NUMBER: _ClassVar[int]
    RERANK_SCORE_PRESENT_FIELD_NUMBER: _ClassVar[int]
    VECTORS_FIELD_NUMBER: _ClassVar[int]
    id: str
    vector: _containers.RepeatedScalarFieldContainer[float]
    creation_time_unix: int
    creation_time_unix_present: bool
    last_update_time_unix: int
    last_update_time_unix_present: bool
    distance: float
    distance_present: bool
    certainty: float
    certainty_present: bool
    score: float
    score_present: bool
    explain_score: str
    explain_score_present: bool
    is_consistent: bool
    generative: str
    generative_present: bool
    is_consistent_present: bool
    vector_bytes: bytes
    id_as_bytes: bytes
    rerank_score: float
    rerank_score_present: bool
    vectors: _containers.RepeatedCompositeFieldContainer[_base_pb2.Vectors]
    def __init__(
        self,
        id: _Optional[str] = ...,
        vector: _Optional[_Iterable[float]] = ...,
        creation_time_unix: _Optional[int] = ...,
        creation_time_unix_present: bool = ...,
        last_update_time_unix: _Optional[int] = ...,
        last_update_time_unix_present: bool = ...,
        distance: _Optional[float] = ...,
        distance_present: bool = ...,
        certainty: _Optional[float] = ...,
        certainty_present: bool = ...,
        score: _Optional[float] = ...,
        score_present: bool = ...,
        explain_score: _Optional[str] = ...,
        explain_score_present: bool = ...,
        is_consistent: bool = ...,
        generative: _Optional[str] = ...,
        generative_present: bool = ...,
        is_consistent_present: bool = ...,
        vector_bytes: _Optional[bytes] = ...,
        id_as_bytes: _Optional[bytes] = ...,
        rerank_score: _Optional[float] = ...,
        rerank_score_present: bool = ...,
        vectors: _Optional[_Iterable[_Union[_base_pb2.Vectors, _Mapping]]] = ...,
    ) -> None: ...

class PropertiesResult(_message.Message):
    __slots__ = (
        "non_ref_properties",
        "ref_props",
        "target_collection",
        "metadata",
        "number_array_properties",
        "int_array_properties",
        "text_array_properties",
        "boolean_array_properties",
        "object_properties",
        "object_array_properties",
        "non_ref_props",
        "ref_props_requested",
    )
    NON_REF_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    REF_PROPS_FIELD_NUMBER: _ClassVar[int]
    TARGET_COLLECTION_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    NUMBER_ARRAY_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    INT_ARRAY_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    TEXT_ARRAY_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    BOOLEAN_ARRAY_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    OBJECT_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ARRAY_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    NON_REF_PROPS_FIELD_NUMBER: _ClassVar[int]
    REF_PROPS_REQUESTED_FIELD_NUMBER: _ClassVar[int]
    non_ref_properties: _struct_pb2.Struct
    ref_props: _containers.RepeatedCompositeFieldContainer[RefPropertiesResult]
    target_collection: str
    metadata: MetadataResult
    number_array_properties: _containers.RepeatedCompositeFieldContainer[
        _base_pb2.NumberArrayProperties
    ]
    int_array_properties: _containers.RepeatedCompositeFieldContainer[_base_pb2.IntArrayProperties]
    text_array_properties: _containers.RepeatedCompositeFieldContainer[
        _base_pb2.TextArrayProperties
    ]
    boolean_array_properties: _containers.RepeatedCompositeFieldContainer[
        _base_pb2.BooleanArrayProperties
    ]
    object_properties: _containers.RepeatedCompositeFieldContainer[_base_pb2.ObjectProperties]
    object_array_properties: _containers.RepeatedCompositeFieldContainer[
        _base_pb2.ObjectArrayProperties
    ]
    non_ref_props: _properties_pb2.Properties
    ref_props_requested: bool
    def __init__(
        self,
        non_ref_properties: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...,
        ref_props: _Optional[_Iterable[_Union[RefPropertiesResult, _Mapping]]] = ...,
        target_collection: _Optional[str] = ...,
        metadata: _Optional[_Union[MetadataResult, _Mapping]] = ...,
        number_array_properties: _Optional[
            _Iterable[_Union[_base_pb2.NumberArrayProperties, _Mapping]]
        ] = ...,
        int_array_properties: _Optional[
            _Iterable[_Union[_base_pb2.IntArrayProperties, _Mapping]]
        ] = ...,
        text_array_properties: _Optional[
            _Iterable[_Union[_base_pb2.TextArrayProperties, _Mapping]]
        ] = ...,
        boolean_array_properties: _Optional[
            _Iterable[_Union[_base_pb2.BooleanArrayProperties, _Mapping]]
        ] = ...,
        object_properties: _Optional[_Iterable[_Union[_base_pb2.ObjectProperties, _Mapping]]] = ...,
        object_array_properties: _Optional[
            _Iterable[_Union[_base_pb2.ObjectArrayProperties, _Mapping]]
        ] = ...,
        non_ref_props: _Optional[_Union[_properties_pb2.Properties, _Mapping]] = ...,
        ref_props_requested: bool = ...,
    ) -> None: ...

class RefPropertiesResult(_message.Message):
    __slots__ = ("properties", "prop_name")
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    PROP_NAME_FIELD_NUMBER: _ClassVar[int]
    properties: _containers.RepeatedCompositeFieldContainer[PropertiesResult]
    prop_name: str
    def __init__(
        self,
        properties: _Optional[_Iterable[_Union[PropertiesResult, _Mapping]]] = ...,
        prop_name: _Optional[str] = ...,
    ) -> None: ...
