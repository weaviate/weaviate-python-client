from google.protobuf import struct_pb2 as _struct_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class BatchObjectsRequest(_message.Message):
    __slots__ = ["objects"]
    OBJECTS_FIELD_NUMBER: _ClassVar[int]
    objects: _containers.RepeatedCompositeFieldContainer[BatchObject]
    def __init__(self, objects: _Optional[_Iterable[_Union[BatchObject, _Mapping]]] = ...) -> None: ...

class BatchObject(_message.Message):
    __slots__ = ["uuid", "vector", "properties", "class_name", "tenant"]
    class Properties(_message.Message):
        __slots__ = ["non_ref_properties", "ref_props_single", "ref_props_multi"]
        NON_REF_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
        REF_PROPS_SINGLE_FIELD_NUMBER: _ClassVar[int]
        REF_PROPS_MULTI_FIELD_NUMBER: _ClassVar[int]
        non_ref_properties: _struct_pb2.Struct
        ref_props_single: _containers.RepeatedCompositeFieldContainer[BatchObject.RefPropertiesSingleTarget]
        ref_props_multi: _containers.RepeatedCompositeFieldContainer[BatchObject.RefPropertiesMultiTarget]
        def __init__(self, non_ref_properties: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ..., ref_props_single: _Optional[_Iterable[_Union[BatchObject.RefPropertiesSingleTarget, _Mapping]]] = ..., ref_props_multi: _Optional[_Iterable[_Union[BatchObject.RefPropertiesMultiTarget, _Mapping]]] = ...) -> None: ...
    class RefPropertiesSingleTarget(_message.Message):
        __slots__ = ["uuids", "prop_name"]
        UUIDS_FIELD_NUMBER: _ClassVar[int]
        PROP_NAME_FIELD_NUMBER: _ClassVar[int]
        uuids: _containers.RepeatedScalarFieldContainer[str]
        prop_name: str
        def __init__(self, uuids: _Optional[_Iterable[str]] = ..., prop_name: _Optional[str] = ...) -> None: ...
    class RefPropertiesMultiTarget(_message.Message):
        __slots__ = ["uuids", "prop_name", "target_collection"]
        UUIDS_FIELD_NUMBER: _ClassVar[int]
        PROP_NAME_FIELD_NUMBER: _ClassVar[int]
        TARGET_COLLECTION_FIELD_NUMBER: _ClassVar[int]
        uuids: _containers.RepeatedScalarFieldContainer[str]
        prop_name: str
        target_collection: str
        def __init__(self, uuids: _Optional[_Iterable[str]] = ..., prop_name: _Optional[str] = ..., target_collection: _Optional[str] = ...) -> None: ...
    UUID_FIELD_NUMBER: _ClassVar[int]
    VECTOR_FIELD_NUMBER: _ClassVar[int]
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    CLASS_NAME_FIELD_NUMBER: _ClassVar[int]
    TENANT_FIELD_NUMBER: _ClassVar[int]
    uuid: str
    vector: _containers.RepeatedScalarFieldContainer[float]
    properties: BatchObject.Properties
    class_name: str
    tenant: str
    def __init__(self, uuid: _Optional[str] = ..., vector: _Optional[_Iterable[float]] = ..., properties: _Optional[_Union[BatchObject.Properties, _Mapping]] = ..., class_name: _Optional[str] = ..., tenant: _Optional[str] = ...) -> None: ...

class BatchObjectsReply(_message.Message):
    __slots__ = ["results", "took"]
    class BatchResults(_message.Message):
        __slots__ = ["index", "error"]
        INDEX_FIELD_NUMBER: _ClassVar[int]
        ERROR_FIELD_NUMBER: _ClassVar[int]
        index: int
        error: str
        def __init__(self, index: _Optional[int] = ..., error: _Optional[str] = ...) -> None: ...
    RESULTS_FIELD_NUMBER: _ClassVar[int]
    TOOK_FIELD_NUMBER: _ClassVar[int]
    results: _containers.RepeatedCompositeFieldContainer[BatchObjectsReply.BatchResults]
    took: float
    def __init__(self, results: _Optional[_Iterable[_Union[BatchObjectsReply.BatchResults, _Mapping]]] = ..., took: _Optional[float] = ...) -> None: ...

class SearchRequest(_message.Message):
    __slots__ = ["class_name", "limit", "additional_properties", "near_vector", "near_object", "properties", "hybrid_search", "bm25_search", "offset", "autocut", "after", "tenant", "filters", "near_text", "near_image", "near_audio", "near_video"]
    CLASS_NAME_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    ADDITIONAL_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    NEAR_VECTOR_FIELD_NUMBER: _ClassVar[int]
    NEAR_OBJECT_FIELD_NUMBER: _ClassVar[int]
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    HYBRID_SEARCH_FIELD_NUMBER: _ClassVar[int]
    BM25_SEARCH_FIELD_NUMBER: _ClassVar[int]
    OFFSET_FIELD_NUMBER: _ClassVar[int]
    AUTOCUT_FIELD_NUMBER: _ClassVar[int]
    AFTER_FIELD_NUMBER: _ClassVar[int]
    TENANT_FIELD_NUMBER: _ClassVar[int]
    FILTERS_FIELD_NUMBER: _ClassVar[int]
    NEAR_TEXT_FIELD_NUMBER: _ClassVar[int]
    NEAR_IMAGE_FIELD_NUMBER: _ClassVar[int]
    NEAR_AUDIO_FIELD_NUMBER: _ClassVar[int]
    NEAR_VIDEO_FIELD_NUMBER: _ClassVar[int]
    class_name: str
    limit: int
    additional_properties: AdditionalProperties
    near_vector: NearVectorParams
    near_object: NearObjectParams
    properties: Properties
    hybrid_search: HybridSearchParams
    bm25_search: BM25SearchParams
    offset: int
    autocut: int
    after: str
    tenant: str
    filters: Filters
    near_text: NearTextSearchParams
    near_image: NearImageSearchParams
    near_audio: NearAudioSearchParams
    near_video: NearVideoSearchParams
    def __init__(self, class_name: _Optional[str] = ..., limit: _Optional[int] = ..., additional_properties: _Optional[_Union[AdditionalProperties, _Mapping]] = ..., near_vector: _Optional[_Union[NearVectorParams, _Mapping]] = ..., near_object: _Optional[_Union[NearObjectParams, _Mapping]] = ..., properties: _Optional[_Union[Properties, _Mapping]] = ..., hybrid_search: _Optional[_Union[HybridSearchParams, _Mapping]] = ..., bm25_search: _Optional[_Union[BM25SearchParams, _Mapping]] = ..., offset: _Optional[int] = ..., autocut: _Optional[int] = ..., after: _Optional[str] = ..., tenant: _Optional[str] = ..., filters: _Optional[_Union[Filters, _Mapping]] = ..., near_text: _Optional[_Union[NearTextSearchParams, _Mapping]] = ..., near_image: _Optional[_Union[NearImageSearchParams, _Mapping]] = ..., near_audio: _Optional[_Union[NearAudioSearchParams, _Mapping]] = ..., near_video: _Optional[_Union[NearVideoSearchParams, _Mapping]] = ...) -> None: ...

class TextArray(_message.Message):
    __slots__ = ["vals"]
    VALS_FIELD_NUMBER: _ClassVar[int]
    vals: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, vals: _Optional[_Iterable[str]] = ...) -> None: ...

class IntArray(_message.Message):
    __slots__ = ["vals"]
    VALS_FIELD_NUMBER: _ClassVar[int]
    vals: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, vals: _Optional[_Iterable[int]] = ...) -> None: ...

class IntArrayProperties(_message.Message):
    __slots__ = ["key", "vals"]
    KEY_FIELD_NUMBER: _ClassVar[int]
    VALS_FIELD_NUMBER: _ClassVar[int]
    key: str
    vals: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, key: _Optional[str] = ..., vals: _Optional[_Iterable[int]] = ...) -> None: ...

class NearObjectParams(_message.Message):
    __slots__ = ["certainty", "distance", "id"]
    CERTAINTY_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    certainty: float
    distance: float
    id: str
    def __init__(self, id: _Optional[str] = ..., certainty: _Optional[float] = ..., distance: _Optional[float] = ...) -> None: ...

class NearTextSearchParams(_message.Message):
    __slots__ = ["certainty", "distance", "move_away", "move_to", "query"]
    class Move(_message.Message):
        __slots__ = ["concepts", "force", "uuids"]
        CONCEPTS_FIELD_NUMBER: _ClassVar[int]
        FORCE_FIELD_NUMBER: _ClassVar[int]
        UUIDS_FIELD_NUMBER: _ClassVar[int]
        concepts: _containers.RepeatedScalarFieldContainer[str]
        force: float
        uuids: _containers.RepeatedScalarFieldContainer[str]
        def __init__(self, force: _Optional[float] = ..., concepts: _Optional[_Iterable[str]] = ..., uuids: _Optional[_Iterable[str]] = ...) -> None: ...
    CERTAINTY_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    MOVE_AWAY_FIELD_NUMBER: _ClassVar[int]
    MOVE_TO_FIELD_NUMBER: _ClassVar[int]
    QUERY_FIELD_NUMBER: _ClassVar[int]
    certainty: float
    distance: float
    move_away: NearTextSearchParams.Move
    move_to: NearTextSearchParams.Move
    query: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, query: _Optional[_Iterable[str]] = ..., certainty: _Optional[float] = ..., distance: _Optional[float] = ..., move_to: _Optional[_Union[NearTextSearchParams.Move, _Mapping]] = ..., move_away: _Optional[_Union[NearTextSearchParams.Move, _Mapping]] = ...) -> None: ...

class NearVectorParams(_message.Message):
    __slots__ = ["certainty", "distance", "vector"]
    CERTAINTY_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    VECTOR_FIELD_NUMBER: _ClassVar[int]
    certainty: float
    distance: float
    vector: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, vector: _Optional[_Iterable[float]] = ..., certainty: _Optional[float] = ..., distance: _Optional[float] = ...) -> None: ...

class NumberArray(_message.Message):
    __slots__ = ["vals"]
    VALS_FIELD_NUMBER: _ClassVar[int]
    vals: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, vals: _Optional[_Iterable[float]] = ...) -> None: ...

class BooleanArray(_message.Message):
    __slots__ = ["vals"]
    VALS_FIELD_NUMBER: _ClassVar[int]
    vals: _containers.RepeatedScalarFieldContainer[bool]
    def __init__(self, vals: _Optional[_Iterable[bool]] = ...) -> None: ...

class DateArray(_message.Message):
    __slots__ = ["vals"]
    VALS_FIELD_NUMBER: _ClassVar[int]
    vals: _containers.RepeatedCompositeFieldContainer[_timestamp_pb2.Timestamp]
    def __init__(self, vals: _Optional[_Iterable[_Union[_timestamp_pb2.Timestamp, _Mapping]]] = ...) -> None: ...

class Filters(_message.Message):
    __slots__ = ["operator", "on", "filters", "value_text", "value_int", "value_boolean", "value_number", "value_date", "value_text_array", "value_int_array", "value_boolean_array", "value_number_array", "value_date_array"]
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
    VALUE_DATE_FIELD_NUMBER: _ClassVar[int]
    VALUE_TEXT_ARRAY_FIELD_NUMBER: _ClassVar[int]
    VALUE_INT_ARRAY_FIELD_NUMBER: _ClassVar[int]
    VALUE_BOOLEAN_ARRAY_FIELD_NUMBER: _ClassVar[int]
    VALUE_NUMBER_ARRAY_FIELD_NUMBER: _ClassVar[int]
    VALUE_DATE_ARRAY_FIELD_NUMBER: _ClassVar[int]
    operator: Filters.Operator
    on: _containers.RepeatedScalarFieldContainer[str]
    filters: _containers.RepeatedCompositeFieldContainer[Filters]
    value_text: str
    value_int: int
    value_boolean: bool
    value_number: float
    value_date: _timestamp_pb2.Timestamp
    value_text_array: TextArray
    value_int_array: IntArray
    value_boolean_array: BooleanArray
    value_number_array: NumberArray
    value_date_array: DateArray
    def __init__(self, operator: _Optional[_Union[Filters.Operator, str]] = ..., on: _Optional[_Iterable[str]] = ..., filters: _Optional[_Iterable[_Union[Filters, _Mapping]]] = ..., value_text: _Optional[str] = ..., value_int: _Optional[int] = ..., value_boolean: bool = ..., value_number: _Optional[float] = ..., value_date: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ..., value_text_array: _Optional[_Union[TextArray, _Mapping]] = ..., value_int_array: _Optional[_Union[IntArray, _Mapping]] = ..., value_boolean_array: _Optional[_Union[BooleanArray, _Mapping]] = ..., value_number_array: _Optional[_Union[NumberArray, _Mapping]] = ..., value_date_array: _Optional[_Union[DateArray, _Mapping]] = ...) -> None: ...

class AdditionalProperties(_message.Message):
    __slots__ = ["uuid", "vector", "creationTimeUnix", "lastUpdateTimeUnix", "distance", "certainty", "score", "explainScore"]
    UUID_FIELD_NUMBER: _ClassVar[int]
    VECTOR_FIELD_NUMBER: _ClassVar[int]
    CREATIONTIMEUNIX_FIELD_NUMBER: _ClassVar[int]
    LASTUPDATETIMEUNIX_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    CERTAINTY_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    EXPLAINSCORE_FIELD_NUMBER: _ClassVar[int]
    uuid: bool
    vector: bool
    creationTimeUnix: bool
    lastUpdateTimeUnix: bool
    distance: bool
    certainty: bool
    score: bool
    explainScore: bool
    def __init__(self, uuid: bool = ..., vector: bool = ..., creationTimeUnix: bool = ..., lastUpdateTimeUnix: bool = ..., distance: bool = ..., certainty: bool = ..., score: bool = ..., explainScore: bool = ...) -> None: ...

class Properties(_message.Message):
    __slots__ = ["non_ref_properties", "ref_properties"]
    NON_REF_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    REF_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    non_ref_properties: _containers.RepeatedScalarFieldContainer[str]
    ref_properties: _containers.RepeatedCompositeFieldContainer[RefProperties]
    def __init__(self, non_ref_properties: _Optional[_Iterable[str]] = ..., ref_properties: _Optional[_Iterable[_Union[RefProperties, _Mapping]]] = ...) -> None: ...

class HybridSearchParams(_message.Message):
    __slots__ = ["query", "properties", "vector", "alpha", "fusion_type"]
    class FusionType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
        FUSION_TYPE_UNSPECIFIED: _ClassVar[HybridSearchParams.FusionType]
        FUSION_TYPE_RANKED: _ClassVar[HybridSearchParams.FusionType]
        FUSION_TYPE_RELATIVE_SCORE: _ClassVar[HybridSearchParams.FusionType]
    FUSION_TYPE_UNSPECIFIED: HybridSearchParams.FusionType
    FUSION_TYPE_RANKED: HybridSearchParams.FusionType
    FUSION_TYPE_RELATIVE_SCORE: HybridSearchParams.FusionType
    QUERY_FIELD_NUMBER: _ClassVar[int]
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    VECTOR_FIELD_NUMBER: _ClassVar[int]
    ALPHA_FIELD_NUMBER: _ClassVar[int]
    FUSION_TYPE_FIELD_NUMBER: _ClassVar[int]
    query: str
    properties: _containers.RepeatedScalarFieldContainer[str]
    vector: _containers.RepeatedScalarFieldContainer[float]
    alpha: float
    fusion_type: HybridSearchParams.FusionType
    def __init__(self, query: _Optional[str] = ..., properties: _Optional[_Iterable[str]] = ..., vector: _Optional[_Iterable[float]] = ..., alpha: _Optional[float] = ..., fusion_type: _Optional[_Union[HybridSearchParams.FusionType, str]] = ...) -> None: ...

class NearTextSearchParams(_message.Message):
    __slots__ = ["query", "certainty", "distance", "move_to", "move_away"]
    class Move(_message.Message):
        __slots__ = ["force", "concepts", "uuids"]
        FORCE_FIELD_NUMBER: _ClassVar[int]
        CONCEPTS_FIELD_NUMBER: _ClassVar[int]
        UUIDS_FIELD_NUMBER: _ClassVar[int]
        force: float
        concepts: _containers.RepeatedScalarFieldContainer[str]
        uuids: _containers.RepeatedScalarFieldContainer[str]
        def __init__(self, force: _Optional[float] = ..., concepts: _Optional[_Iterable[str]] = ..., uuids: _Optional[_Iterable[str]] = ...) -> None: ...
    QUERY_FIELD_NUMBER: _ClassVar[int]
    CERTAINTY_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    MOVE_TO_FIELD_NUMBER: _ClassVar[int]
    MOVE_AWAY_FIELD_NUMBER: _ClassVar[int]
    query: _containers.RepeatedScalarFieldContainer[str]
    certainty: float
    distance: float
    move_to: NearTextSearchParams.Move
    move_away: NearTextSearchParams.Move
    def __init__(self, query: _Optional[_Iterable[str]] = ..., certainty: _Optional[float] = ..., distance: _Optional[float] = ..., move_to: _Optional[_Union[NearTextSearchParams.Move, _Mapping]] = ..., move_away: _Optional[_Union[NearTextSearchParams.Move, _Mapping]] = ...) -> None: ...

class NearImageSearchParams(_message.Message):
    __slots__ = ["image", "certainty", "distance"]
    IMAGE_FIELD_NUMBER: _ClassVar[int]
    CERTAINTY_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    image: str
    certainty: float
    distance: float
    def __init__(self, image: _Optional[str] = ..., certainty: _Optional[float] = ..., distance: _Optional[float] = ...) -> None: ...

class NearAudioSearchParams(_message.Message):
    __slots__ = ["audio", "certainty", "distance"]
    AUDIO_FIELD_NUMBER: _ClassVar[int]
    CERTAINTY_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    audio: str
    certainty: float
    distance: float
    def __init__(self, audio: _Optional[str] = ..., certainty: _Optional[float] = ..., distance: _Optional[float] = ...) -> None: ...

class NearVideoSearchParams(_message.Message):
    __slots__ = ["video", "certainty", "distance"]
    VIDEO_FIELD_NUMBER: _ClassVar[int]
    CERTAINTY_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    video: str
    certainty: float
    distance: float
    def __init__(self, video: _Optional[str] = ..., certainty: _Optional[float] = ..., distance: _Optional[float] = ...) -> None: ...

class BM25SearchParams(_message.Message):
    __slots__ = ["query", "properties"]
    QUERY_FIELD_NUMBER: _ClassVar[int]
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    query: str
    properties: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, query: _Optional[str] = ..., properties: _Optional[_Iterable[str]] = ...) -> None: ...

class RefProperties(_message.Message):
    __slots__ = ["reference_property", "linked_properties", "metadata", "which_collection"]
    REFERENCE_PROPERTY_FIELD_NUMBER: _ClassVar[int]
    LINKED_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    WHICH_COLLECTION_FIELD_NUMBER: _ClassVar[int]
    reference_property: str
    linked_properties: Properties
    metadata: AdditionalProperties
    which_collection: str
    def __init__(self, reference_property: _Optional[str] = ..., linked_properties: _Optional[_Union[Properties, _Mapping]] = ..., metadata: _Optional[_Union[AdditionalProperties, _Mapping]] = ..., which_collection: _Optional[str] = ...) -> None: ...

class NearVectorParams(_message.Message):
    __slots__ = ["vector", "certainty", "distance"]
    VECTOR_FIELD_NUMBER: _ClassVar[int]
    CERTAINTY_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    vector: _containers.RepeatedScalarFieldContainer[float]
    certainty: float
    distance: float
    def __init__(self, vector: _Optional[_Iterable[float]] = ..., certainty: _Optional[float] = ..., distance: _Optional[float] = ...) -> None: ...

class NearObjectParams(_message.Message):
    __slots__ = ["id", "certainty", "distance"]
    ID_FIELD_NUMBER: _ClassVar[int]
    CERTAINTY_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    id: str
    certainty: float
    distance: float
    def __init__(self, id: _Optional[str] = ..., certainty: _Optional[float] = ..., distance: _Optional[float] = ...) -> None: ...

class SearchReply(_message.Message):
    __slots__ = ["results", "took"]
    RESULTS_FIELD_NUMBER: _ClassVar[int]
    TOOK_FIELD_NUMBER: _ClassVar[int]
    results: _containers.RepeatedCompositeFieldContainer[SearchResult]
    took: float
    def __init__(self, results: _Optional[_Iterable[_Union[SearchResult, _Mapping]]] = ..., took: _Optional[float] = ...) -> None: ...

class SearchRequest(_message.Message):
    __slots__ = ["additional_properties", "after", "autocut", "bm25_search", "class_name", "filters", "hybrid_search", "limit", "near_object", "near_text", "near_vector", "offset", "properties", "tenant"]
    ADDITIONAL_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    AFTER_FIELD_NUMBER: _ClassVar[int]
    AUTOCUT_FIELD_NUMBER: _ClassVar[int]
    BM25_SEARCH_FIELD_NUMBER: _ClassVar[int]
    CLASS_NAME_FIELD_NUMBER: _ClassVar[int]
    FILTERS_FIELD_NUMBER: _ClassVar[int]
    HYBRID_SEARCH_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    NEAR_OBJECT_FIELD_NUMBER: _ClassVar[int]
    NEAR_TEXT_FIELD_NUMBER: _ClassVar[int]
    NEAR_VECTOR_FIELD_NUMBER: _ClassVar[int]
    OFFSET_FIELD_NUMBER: _ClassVar[int]
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    TENANT_FIELD_NUMBER: _ClassVar[int]
    additional_properties: AdditionalProperties
    after: str
    autocut: int
    bm25_search: BM25SearchParams
    class_name: str
    filters: Filters
    hybrid_search: HybridSearchParams
    limit: int
    near_object: NearObjectParams
    near_text: NearTextSearchParams
    near_vector: NearVectorParams
    offset: int
    properties: Properties
    tenant: str
    def __init__(self, class_name: _Optional[str] = ..., limit: _Optional[int] = ..., additional_properties: _Optional[_Union[AdditionalProperties, _Mapping]] = ..., near_vector: _Optional[_Union[NearVectorParams, _Mapping]] = ..., near_object: _Optional[_Union[NearObjectParams, _Mapping]] = ..., properties: _Optional[_Union[Properties, _Mapping]] = ..., hybrid_search: _Optional[_Union[HybridSearchParams, _Mapping]] = ..., bm25_search: _Optional[_Union[BM25SearchParams, _Mapping]] = ..., offset: _Optional[int] = ..., autocut: _Optional[int] = ..., after: _Optional[str] = ..., tenant: _Optional[str] = ..., filters: _Optional[_Union[Filters, _Mapping]] = ..., near_text: _Optional[_Union[NearTextSearchParams, _Mapping]] = ...) -> None: ...

class SearchResult(_message.Message):
    __slots__ = ["properties", "additional_properties"]
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    ADDITIONAL_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    properties: ResultProperties
    additional_properties: ResultAdditionalProps
    def __init__(self, properties: _Optional[_Union[ResultProperties, _Mapping]] = ..., additional_properties: _Optional[_Union[ResultAdditionalProps, _Mapping]] = ...) -> None: ...

class ResultAdditionalProps(_message.Message):
    __slots__ = ["id", "vector", "creation_time_unix", "creation_time_unix_present", "last_update_time_unix", "last_update_time_unix_present", "distance", "distance_present", "certainty", "certainty_present", "score", "score_present", "explain_score", "explain_score_present"]
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
    def __init__(self, id: _Optional[str] = ..., vector: _Optional[_Iterable[float]] = ..., creation_time_unix: _Optional[int] = ..., creation_time_unix_present: bool = ..., last_update_time_unix: _Optional[int] = ..., last_update_time_unix_present: bool = ..., distance: _Optional[float] = ..., distance_present: bool = ..., certainty: _Optional[float] = ..., certainty_present: bool = ..., score: _Optional[float] = ..., score_present: bool = ..., explain_score: _Optional[str] = ..., explain_score_present: bool = ...) -> None: ...

class NumberArrayProperties(_message.Message):
    __slots__ = ["key", "vals"]
    KEY_FIELD_NUMBER: _ClassVar[int]
    VALS_FIELD_NUMBER: _ClassVar[int]
    key: str
    vals: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, key: _Optional[str] = ..., vals: _Optional[_Iterable[float]] = ...) -> None: ...

class IntArrayProperties(_message.Message):
    __slots__ = ["key", "vals"]
    KEY_FIELD_NUMBER: _ClassVar[int]
    VALS_FIELD_NUMBER: _ClassVar[int]
    key: str
    vals: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, key: _Optional[str] = ..., vals: _Optional[_Iterable[int]] = ...) -> None: ...

class TextArrayProperties(_message.Message):
    __slots__ = ["key", "vals"]
    KEY_FIELD_NUMBER: _ClassVar[int]
    VALS_FIELD_NUMBER: _ClassVar[int]
    key: str
    vals: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, key: _Optional[str] = ..., vals: _Optional[_Iterable[str]] = ...) -> None: ...

class BooleanArrayProperties(_message.Message):
    __slots__ = ["key", "vals"]
    KEY_FIELD_NUMBER: _ClassVar[int]
    VALS_FIELD_NUMBER: _ClassVar[int]
    key: str
    vals: _containers.RepeatedScalarFieldContainer[bool]
    def __init__(self, key: _Optional[str] = ..., vals: _Optional[_Iterable[bool]] = ...) -> None: ...

class DateArrayProperties(_message.Message):
    __slots__ = ["key", "vals"]
    KEY_FIELD_NUMBER: _ClassVar[int]
    VALS_FIELD_NUMBER: _ClassVar[int]
    key: str
    vals: _containers.RepeatedCompositeFieldContainer[_timestamp_pb2.Timestamp]
    def __init__(self, key: _Optional[str] = ..., vals: _Optional[_Iterable[_Union[_timestamp_pb2.Timestamp, _Mapping]]] = ...) -> None: ...

class UuidArrayProperties(_message.Message):
    __slots__ = ["key", "vals"]
    KEY_FIELD_NUMBER: _ClassVar[int]
    VALS_FIELD_NUMBER: _ClassVar[int]
    key: str
    vals: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, key: _Optional[str] = ..., vals: _Optional[_Iterable[str]] = ...) -> None: ...

class ResultProperties(_message.Message):
    __slots__ = ["non_ref_properties", "ref_props", "class_name", "metadata", "number_array_properties", "int_array_properties", "text_array_properties", "boolean_array_properties", "uuid_array_properties"]
    NON_REF_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    REF_PROPS_FIELD_NUMBER: _ClassVar[int]
    CLASS_NAME_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    NUMBER_ARRAY_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    INT_ARRAY_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    TEXT_ARRAY_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    BOOLEAN_ARRAY_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    UUID_ARRAY_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    non_ref_properties: _struct_pb2.Struct
    ref_props: _containers.RepeatedCompositeFieldContainer[ReturnRefProperties]
    class_name: str
    metadata: ResultAdditionalProps
    number_array_properties: _containers.RepeatedCompositeFieldContainer[NumberArrayProperties]
    int_array_properties: _containers.RepeatedCompositeFieldContainer[IntArrayProperties]
    text_array_properties: _containers.RepeatedCompositeFieldContainer[TextArrayProperties]
    boolean_array_properties: _containers.RepeatedCompositeFieldContainer[BooleanArrayProperties]
    uuid_array_properties: _containers.RepeatedCompositeFieldContainer[UuidArrayProperties]
    def __init__(self, non_ref_properties: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ..., ref_props: _Optional[_Iterable[_Union[ReturnRefProperties, _Mapping]]] = ..., class_name: _Optional[str] = ..., metadata: _Optional[_Union[ResultAdditionalProps, _Mapping]] = ..., number_array_properties: _Optional[_Iterable[_Union[NumberArrayProperties, _Mapping]]] = ..., int_array_properties: _Optional[_Iterable[_Union[IntArrayProperties, _Mapping]]] = ..., text_array_properties: _Optional[_Iterable[_Union[TextArrayProperties, _Mapping]]] = ..., boolean_array_properties: _Optional[_Iterable[_Union[BooleanArrayProperties, _Mapping]]] = ..., uuid_array_properties: _Optional[_Iterable[_Union[UuidArrayProperties, _Mapping]]] = ...) -> None: ...

class ReturnRefProperties(_message.Message):
    __slots__ = ["properties", "prop_name"]
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    PROP_NAME_FIELD_NUMBER: _ClassVar[int]
    properties: _containers.RepeatedCompositeFieldContainer[ResultProperties]
    prop_name: str
    def __init__(self, properties: _Optional[_Iterable[_Union[ResultProperties, _Mapping]]] = ..., prop_name: _Optional[str] = ...) -> None: ...
