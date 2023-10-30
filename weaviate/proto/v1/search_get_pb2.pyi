from google.protobuf import struct_pb2 as _struct_pb2
from v1 import base_pb2 as _base_pb2
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

class SearchRequest(_message.Message):
    __slots__ = [
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
        "generative",
    ]
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
    GENERATIVE_FIELD_NUMBER: _ClassVar[int]
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
    filters: Filters
    hybrid_search: Hybrid
    bm25_search: BM25
    near_vector: NearVector
    near_object: NearObject
    near_text: NearTextSearch
    near_image: NearImageSearch
    near_audio: NearAudioSearch
    near_video: NearVideoSearch
    generative: GenerativeSearch
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
        filters: _Optional[_Union[Filters, _Mapping]] = ...,
        hybrid_search: _Optional[_Union[Hybrid, _Mapping]] = ...,
        bm25_search: _Optional[_Union[BM25, _Mapping]] = ...,
        near_vector: _Optional[_Union[NearVector, _Mapping]] = ...,
        near_object: _Optional[_Union[NearObject, _Mapping]] = ...,
        near_text: _Optional[_Union[NearTextSearch, _Mapping]] = ...,
        near_image: _Optional[_Union[NearImageSearch, _Mapping]] = ...,
        near_audio: _Optional[_Union[NearAudioSearch, _Mapping]] = ...,
        near_video: _Optional[_Union[NearVideoSearch, _Mapping]] = ...,
        generative: _Optional[_Union[GenerativeSearch, _Mapping]] = ...,
    ) -> None: ...

class GroupBy(_message.Message):
    __slots__ = ["path", "number_of_groups", "objects_per_group"]
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
    __slots__ = ["ascending", "path"]
    ASCENDING_FIELD_NUMBER: _ClassVar[int]
    PATH_FIELD_NUMBER: _ClassVar[int]
    ascending: bool
    path: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, ascending: bool = ..., path: _Optional[_Iterable[str]] = ...) -> None: ...

class GenerativeSearch(_message.Message):
    __slots__ = ["single_response_prompt", "grouped_response_task", "grouped_properties"]
    SINGLE_RESPONSE_PROMPT_FIELD_NUMBER: _ClassVar[int]
    GROUPED_RESPONSE_TASK_FIELD_NUMBER: _ClassVar[int]
    GROUPED_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    single_response_prompt: str
    grouped_response_task: str
    grouped_properties: _containers.RepeatedScalarFieldContainer[str]
    def __init__(
        self,
        single_response_prompt: _Optional[str] = ...,
        grouped_response_task: _Optional[str] = ...,
        grouped_properties: _Optional[_Iterable[str]] = ...,
    ) -> None: ...

class TextArray(_message.Message):
    __slots__ = ["values"]
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, values: _Optional[_Iterable[str]] = ...) -> None: ...

class IntArray(_message.Message):
    __slots__ = ["values"]
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, values: _Optional[_Iterable[int]] = ...) -> None: ...

class NumberArray(_message.Message):
    __slots__ = ["values"]
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, values: _Optional[_Iterable[float]] = ...) -> None: ...

class BooleanArray(_message.Message):
    __slots__ = ["values"]
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[bool]
    def __init__(self, values: _Optional[_Iterable[bool]] = ...) -> None: ...

class Filters(_message.Message):
    __slots__ = [
        "operator",
        "on",
        "filters",
        "value_text",
        "value_int",
        "value_boolean",
        "value_number",
        "value_text_array",
        "value_int_array",
        "value_boolean_array",
        "value_number_array",
    ]

    class Operator(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
        OPERATOR_UNSPECIFIED: _ClassVar[Filters.Operator]
        OPERATOR_EQUAL: _ClassVar[Filters.Operator]
        OPERATOR_NOT_EQUAL: _ClassVar[Filters.Operator]
        OPERATOR_GREATER_THAN: _ClassVar[Filters.Operator]
        OPERATOR_GREATER_THAN_EQUAL: _ClassVar[Filters.Operator]
        OPERATOR_LESS_THAN: _ClassVar[Filters.Operator]
        OPERATOR_LESS_THAN_EQUAL: _ClassVar[Filters.Operator]
        OPERATOR_AND: _ClassVar[Filters.Operator]
        OPERATOR_OR: _ClassVar[Filters.Operator]
        OPERATOR_WITHIN_GEO_RANGE: _ClassVar[Filters.Operator]
        OPERATOR_LIKE: _ClassVar[Filters.Operator]
        OPERATOR_IS_NULL: _ClassVar[Filters.Operator]
        OPERATOR_CONTAINS_ANY: _ClassVar[Filters.Operator]
        OPERATOR_CONTAINS_ALL: _ClassVar[Filters.Operator]
    OPERATOR_UNSPECIFIED: Filters.Operator
    OPERATOR_EQUAL: Filters.Operator
    OPERATOR_NOT_EQUAL: Filters.Operator
    OPERATOR_GREATER_THAN: Filters.Operator
    OPERATOR_GREATER_THAN_EQUAL: Filters.Operator
    OPERATOR_LESS_THAN: Filters.Operator
    OPERATOR_LESS_THAN_EQUAL: Filters.Operator
    OPERATOR_AND: Filters.Operator
    OPERATOR_OR: Filters.Operator
    OPERATOR_WITHIN_GEO_RANGE: Filters.Operator
    OPERATOR_LIKE: Filters.Operator
    OPERATOR_IS_NULL: Filters.Operator
    OPERATOR_CONTAINS_ANY: Filters.Operator
    OPERATOR_CONTAINS_ALL: Filters.Operator
    OPERATOR_FIELD_NUMBER: _ClassVar[int]
    ON_FIELD_NUMBER: _ClassVar[int]
    FILTERS_FIELD_NUMBER: _ClassVar[int]
    VALUE_TEXT_FIELD_NUMBER: _ClassVar[int]
    VALUE_INT_FIELD_NUMBER: _ClassVar[int]
    VALUE_BOOLEAN_FIELD_NUMBER: _ClassVar[int]
    VALUE_NUMBER_FIELD_NUMBER: _ClassVar[int]
    VALUE_TEXT_ARRAY_FIELD_NUMBER: _ClassVar[int]
    VALUE_INT_ARRAY_FIELD_NUMBER: _ClassVar[int]
    VALUE_BOOLEAN_ARRAY_FIELD_NUMBER: _ClassVar[int]
    VALUE_NUMBER_ARRAY_FIELD_NUMBER: _ClassVar[int]
    operator: Filters.Operator
    on: _containers.RepeatedScalarFieldContainer[str]
    filters: _containers.RepeatedCompositeFieldContainer[Filters]
    value_text: str
    value_int: int
    value_boolean: bool
    value_number: float
    value_text_array: TextArray
    value_int_array: IntArray
    value_boolean_array: BooleanArray
    value_number_array: NumberArray
    def __init__(
        self,
        operator: _Optional[_Union[Filters.Operator, str]] = ...,
        on: _Optional[_Iterable[str]] = ...,
        filters: _Optional[_Iterable[_Union[Filters, _Mapping]]] = ...,
        value_text: _Optional[str] = ...,
        value_int: _Optional[int] = ...,
        value_boolean: bool = ...,
        value_number: _Optional[float] = ...,
        value_text_array: _Optional[_Union[TextArray, _Mapping]] = ...,
        value_int_array: _Optional[_Union[IntArray, _Mapping]] = ...,
        value_boolean_array: _Optional[_Union[BooleanArray, _Mapping]] = ...,
        value_number_array: _Optional[_Union[NumberArray, _Mapping]] = ...,
    ) -> None: ...

class MetadataRequest(_message.Message):
    __slots__ = [
        "uuid",
        "vector",
        "creation_time_unix",
        "last_update_time_unix",
        "distance",
        "certainty",
        "score",
        "explain_score",
        "is_consistent",
    ]
    UUID_FIELD_NUMBER: _ClassVar[int]
    VECTOR_FIELD_NUMBER: _ClassVar[int]
    CREATION_TIME_UNIX_FIELD_NUMBER: _ClassVar[int]
    LAST_UPDATE_TIME_UNIX_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    CERTAINTY_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    EXPLAIN_SCORE_FIELD_NUMBER: _ClassVar[int]
    IS_CONSISTENT_FIELD_NUMBER: _ClassVar[int]
    uuid: bool
    vector: bool
    creation_time_unix: bool
    last_update_time_unix: bool
    distance: bool
    certainty: bool
    score: bool
    explain_score: bool
    is_consistent: bool
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
    ) -> None: ...

class PropertiesRequest(_message.Message):
    __slots__ = ["non_ref_properties", "ref_properties", "object_properties"]
    NON_REF_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    REF_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    OBJECT_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    non_ref_properties: _containers.RepeatedScalarFieldContainer[str]
    ref_properties: _containers.RepeatedCompositeFieldContainer[RefPropertiesRequest]
    object_properties: _containers.RepeatedCompositeFieldContainer[ObjectPropertiesRequest]
    def __init__(
        self,
        non_ref_properties: _Optional[_Iterable[str]] = ...,
        ref_properties: _Optional[_Iterable[_Union[RefPropertiesRequest, _Mapping]]] = ...,
        object_properties: _Optional[_Iterable[_Union[ObjectPropertiesRequest, _Mapping]]] = ...,
    ) -> None: ...

class ObjectPropertiesRequest(_message.Message):
    __slots__ = ["prop_name", "primitive_properties", "object_properties"]
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

class Hybrid(_message.Message):
    __slots__ = ["query", "properties", "vector", "alpha", "fusion_type"]

    class FusionType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
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
    query: str
    properties: _containers.RepeatedScalarFieldContainer[str]
    vector: _containers.RepeatedScalarFieldContainer[float]
    alpha: float
    fusion_type: Hybrid.FusionType
    def __init__(
        self,
        query: _Optional[str] = ...,
        properties: _Optional[_Iterable[str]] = ...,
        vector: _Optional[_Iterable[float]] = ...,
        alpha: _Optional[float] = ...,
        fusion_type: _Optional[_Union[Hybrid.FusionType, str]] = ...,
    ) -> None: ...

class NearTextSearch(_message.Message):
    __slots__ = ["query", "certainty", "distance", "move_to", "move_away"]

    class Move(_message.Message):
        __slots__ = ["force", "concepts", "uuids"]
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
    query: _containers.RepeatedScalarFieldContainer[str]
    certainty: float
    distance: float
    move_to: NearTextSearch.Move
    move_away: NearTextSearch.Move
    def __init__(
        self,
        query: _Optional[_Iterable[str]] = ...,
        certainty: _Optional[float] = ...,
        distance: _Optional[float] = ...,
        move_to: _Optional[_Union[NearTextSearch.Move, _Mapping]] = ...,
        move_away: _Optional[_Union[NearTextSearch.Move, _Mapping]] = ...,
    ) -> None: ...

class NearImageSearch(_message.Message):
    __slots__ = ["image", "certainty", "distance"]
    IMAGE_FIELD_NUMBER: _ClassVar[int]
    CERTAINTY_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    image: str
    certainty: float
    distance: float
    def __init__(
        self,
        image: _Optional[str] = ...,
        certainty: _Optional[float] = ...,
        distance: _Optional[float] = ...,
    ) -> None: ...

class NearAudioSearch(_message.Message):
    __slots__ = ["audio", "certainty", "distance"]
    AUDIO_FIELD_NUMBER: _ClassVar[int]
    CERTAINTY_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    audio: str
    certainty: float
    distance: float
    def __init__(
        self,
        audio: _Optional[str] = ...,
        certainty: _Optional[float] = ...,
        distance: _Optional[float] = ...,
    ) -> None: ...

class NearVideoSearch(_message.Message):
    __slots__ = ["video", "certainty", "distance"]
    VIDEO_FIELD_NUMBER: _ClassVar[int]
    CERTAINTY_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    video: str
    certainty: float
    distance: float
    def __init__(
        self,
        video: _Optional[str] = ...,
        certainty: _Optional[float] = ...,
        distance: _Optional[float] = ...,
    ) -> None: ...

class BM25(_message.Message):
    __slots__ = ["query", "properties"]
    QUERY_FIELD_NUMBER: _ClassVar[int]
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    query: str
    properties: _containers.RepeatedScalarFieldContainer[str]
    def __init__(
        self, query: _Optional[str] = ..., properties: _Optional[_Iterable[str]] = ...
    ) -> None: ...

class RefPropertiesRequest(_message.Message):
    __slots__ = ["reference_property", "properties", "metadata", "target_collection"]
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

class NearVector(_message.Message):
    __slots__ = ["vector", "certainty", "distance"]
    VECTOR_FIELD_NUMBER: _ClassVar[int]
    CERTAINTY_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    vector: _containers.RepeatedScalarFieldContainer[float]
    certainty: float
    distance: float
    def __init__(
        self,
        vector: _Optional[_Iterable[float]] = ...,
        certainty: _Optional[float] = ...,
        distance: _Optional[float] = ...,
    ) -> None: ...

class NearObject(_message.Message):
    __slots__ = ["id", "certainty", "distance"]
    ID_FIELD_NUMBER: _ClassVar[int]
    CERTAINTY_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    id: str
    certainty: float
    distance: float
    def __init__(
        self,
        id: _Optional[str] = ...,
        certainty: _Optional[float] = ...,
        distance: _Optional[float] = ...,
    ) -> None: ...

class SearchReply(_message.Message):
    __slots__ = ["took", "results", "generative_grouped_result", "group_by_results"]
    TOOK_FIELD_NUMBER: _ClassVar[int]
    RESULTS_FIELD_NUMBER: _ClassVar[int]
    GENERATIVE_GROUPED_RESULT_FIELD_NUMBER: _ClassVar[int]
    GROUP_BY_RESULTS_FIELD_NUMBER: _ClassVar[int]
    took: float
    results: _containers.RepeatedCompositeFieldContainer[SearchResult]
    generative_grouped_result: str
    group_by_results: _containers.RepeatedCompositeFieldContainer[GroupByResult]
    def __init__(
        self,
        took: _Optional[float] = ...,
        results: _Optional[_Iterable[_Union[SearchResult, _Mapping]]] = ...,
        generative_grouped_result: _Optional[str] = ...,
        group_by_results: _Optional[_Iterable[_Union[GroupByResult, _Mapping]]] = ...,
    ) -> None: ...

class GroupByResult(_message.Message):
    __slots__ = ["name", "min_distance", "max_distance", "number_of_objects", "objects"]
    NAME_FIELD_NUMBER: _ClassVar[int]
    MIN_DISTANCE_FIELD_NUMBER: _ClassVar[int]
    MAX_DISTANCE_FIELD_NUMBER: _ClassVar[int]
    NUMBER_OF_OBJECTS_FIELD_NUMBER: _ClassVar[int]
    OBJECTS_FIELD_NUMBER: _ClassVar[int]
    name: str
    min_distance: float
    max_distance: float
    number_of_objects: int
    objects: _containers.RepeatedCompositeFieldContainer[SearchResult]
    def __init__(
        self,
        name: _Optional[str] = ...,
        min_distance: _Optional[float] = ...,
        max_distance: _Optional[float] = ...,
        number_of_objects: _Optional[int] = ...,
        objects: _Optional[_Iterable[_Union[SearchResult, _Mapping]]] = ...,
    ) -> None: ...

class SearchResult(_message.Message):
    __slots__ = ["properties", "metadata"]
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    properties: PropertiesResult
    metadata: MetadataResult
    def __init__(
        self,
        properties: _Optional[_Union[PropertiesResult, _Mapping]] = ...,
        metadata: _Optional[_Union[MetadataResult, _Mapping]] = ...,
    ) -> None: ...

class MetadataResult(_message.Message):
    __slots__ = [
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
    ]
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
    ) -> None: ...

class PropertiesResult(_message.Message):
    __slots__ = [
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
    ]
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
    ) -> None: ...

class RefPropertiesResult(_message.Message):
    __slots__ = ["properties", "prop_name"]
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    PROP_NAME_FIELD_NUMBER: _ClassVar[int]
    properties: _containers.RepeatedCompositeFieldContainer[PropertiesResult]
    prop_name: str
    def __init__(
        self,
        properties: _Optional[_Iterable[_Union[PropertiesResult, _Mapping]]] = ...,
        prop_name: _Optional[str] = ...,
    ) -> None: ...
