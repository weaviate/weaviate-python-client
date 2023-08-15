from google.protobuf import struct_pb2 as _struct_pb2
from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class AdditionalProperties(_message.Message):
    __slots__ = ["certainty", "creationTimeUnix", "distance", "explainScore", "lastUpdateTimeUnix", "score", "uuid", "vector"]
    CERTAINTY_FIELD_NUMBER: _ClassVar[int]
    CREATIONTIMEUNIX_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    EXPLAINSCORE_FIELD_NUMBER: _ClassVar[int]
    LASTUPDATETIMEUNIX_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    UUID_FIELD_NUMBER: _ClassVar[int]
    VECTOR_FIELD_NUMBER: _ClassVar[int]
    certainty: bool
    creationTimeUnix: bool
    distance: bool
    explainScore: bool
    lastUpdateTimeUnix: bool
    score: bool
    uuid: bool
    vector: bool
    def __init__(self, uuid: bool = ..., vector: bool = ..., creationTimeUnix: bool = ..., lastUpdateTimeUnix: bool = ..., distance: bool = ..., certainty: bool = ..., score: bool = ..., explainScore: bool = ...) -> None: ...

class BM25SearchParams(_message.Message):
    __slots__ = ["properties", "query"]
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    QUERY_FIELD_NUMBER: _ClassVar[int]
    properties: _containers.RepeatedScalarFieldContainer[str]
    query: str
    def __init__(self, query: _Optional[str] = ..., properties: _Optional[_Iterable[str]] = ...) -> None: ...

class BatchObject(_message.Message):
    __slots__ = ["class_name", "properties", "tenant", "uuid", "vector"]
    class Properties(_message.Message):
        __slots__ = ["non_ref_properties", "ref_props_multi", "ref_props_single"]
        NON_REF_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
        REF_PROPS_MULTI_FIELD_NUMBER: _ClassVar[int]
        REF_PROPS_SINGLE_FIELD_NUMBER: _ClassVar[int]
        non_ref_properties: _struct_pb2.Struct
        ref_props_multi: _containers.RepeatedCompositeFieldContainer[BatchObject.RefPropertiesMultiTarget]
        ref_props_single: _containers.RepeatedCompositeFieldContainer[BatchObject.RefPropertiesSingleTarget]
        def __init__(self, non_ref_properties: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ..., ref_props_single: _Optional[_Iterable[_Union[BatchObject.RefPropertiesSingleTarget, _Mapping]]] = ..., ref_props_multi: _Optional[_Iterable[_Union[BatchObject.RefPropertiesMultiTarget, _Mapping]]] = ...) -> None: ...
    class RefPropertiesMultiTarget(_message.Message):
        __slots__ = ["prop_name", "target_collection", "uuids"]
        PROP_NAME_FIELD_NUMBER: _ClassVar[int]
        TARGET_COLLECTION_FIELD_NUMBER: _ClassVar[int]
        UUIDS_FIELD_NUMBER: _ClassVar[int]
        prop_name: str
        target_collection: str
        uuids: _containers.RepeatedScalarFieldContainer[str]
        def __init__(self, uuids: _Optional[_Iterable[str]] = ..., prop_name: _Optional[str] = ..., target_collection: _Optional[str] = ...) -> None: ...
    class RefPropertiesSingleTarget(_message.Message):
        __slots__ = ["prop_name", "uuids"]
        PROP_NAME_FIELD_NUMBER: _ClassVar[int]
        UUIDS_FIELD_NUMBER: _ClassVar[int]
        prop_name: str
        uuids: _containers.RepeatedScalarFieldContainer[str]
        def __init__(self, uuids: _Optional[_Iterable[str]] = ..., prop_name: _Optional[str] = ...) -> None: ...
    CLASS_NAME_FIELD_NUMBER: _ClassVar[int]
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    TENANT_FIELD_NUMBER: _ClassVar[int]
    UUID_FIELD_NUMBER: _ClassVar[int]
    VECTOR_FIELD_NUMBER: _ClassVar[int]
    class_name: str
    properties: BatchObject.Properties
    tenant: str
    uuid: str
    vector: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, uuid: _Optional[str] = ..., vector: _Optional[_Iterable[float]] = ..., properties: _Optional[_Union[BatchObject.Properties, _Mapping]] = ..., class_name: _Optional[str] = ..., tenant: _Optional[str] = ...) -> None: ...

class BatchObjectsReply(_message.Message):
    __slots__ = ["results", "took"]
    class BatchResults(_message.Message):
        __slots__ = []
        def __init__(self) -> None: ...
    RESULTS_FIELD_NUMBER: _ClassVar[int]
    TOOK_FIELD_NUMBER: _ClassVar[int]
    results: _containers.RepeatedCompositeFieldContainer[BatchObjectsReply.BatchResults]
    took: float
    def __init__(self, results: _Optional[_Iterable[_Union[BatchObjectsReply.BatchResults, _Mapping]]] = ..., took: _Optional[float] = ...) -> None: ...

class BatchObjectsRequest(_message.Message):
    __slots__ = ["objects"]
    OBJECTS_FIELD_NUMBER: _ClassVar[int]
    objects: _containers.RepeatedCompositeFieldContainer[BatchObject]
    def __init__(self, objects: _Optional[_Iterable[_Union[BatchObject, _Mapping]]] = ...) -> None: ...

class Filters(_message.Message):
    __slots__ = ["filters", "on", "operator", "value_bool", "value_date", "value_float", "value_int", "value_str"]
    class OperatorType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    FILTERS_FIELD_NUMBER: _ClassVar[int]
    ON_FIELD_NUMBER: _ClassVar[int]
    OPERATOR_FIELD_NUMBER: _ClassVar[int]
    OperatorAnd: Filters.OperatorType
    OperatorEqual: Filters.OperatorType
    OperatorGreaterThan: Filters.OperatorType
    OperatorGreaterThanEqual: Filters.OperatorType
    OperatorIsNull: Filters.OperatorType
    OperatorLessThan: Filters.OperatorType
    OperatorLessThanEqual: Filters.OperatorType
    OperatorLike: Filters.OperatorType
    OperatorNotEqual: Filters.OperatorType
    OperatorOr: Filters.OperatorType
    OperatorWithinGeoRange: Filters.OperatorType
    VALUE_BOOL_FIELD_NUMBER: _ClassVar[int]
    VALUE_DATE_FIELD_NUMBER: _ClassVar[int]
    VALUE_FLOAT_FIELD_NUMBER: _ClassVar[int]
    VALUE_INT_FIELD_NUMBER: _ClassVar[int]
    VALUE_STR_FIELD_NUMBER: _ClassVar[int]
    filters: _containers.RepeatedCompositeFieldContainer[Filters]
    on: _containers.RepeatedScalarFieldContainer[str]
    operator: Filters.OperatorType
    value_bool: bool
    value_date: _timestamp_pb2.Timestamp
    value_float: float
    value_int: int
    value_str: str
    def __init__(self, operator: _Optional[_Union[Filters.OperatorType, str]] = ..., on: _Optional[_Iterable[str]] = ..., filters: _Optional[_Iterable[_Union[Filters, _Mapping]]] = ..., value_str: _Optional[str] = ..., value_int: _Optional[int] = ..., value_bool: bool = ..., value_float: _Optional[float] = ..., value_date: _Optional[_Union[_timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class HybridSearchParams(_message.Message):
    __slots__ = ["alpha", "fusion_type", "properties", "query", "vector"]
    class FusionType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
    ALPHA_FIELD_NUMBER: _ClassVar[int]
    FUSION_TYPE_FIELD_NUMBER: _ClassVar[int]
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    QUERY_FIELD_NUMBER: _ClassVar[int]
    RANKED: HybridSearchParams.FusionType
    RELATIVE_SCORE: HybridSearchParams.FusionType
    VECTOR_FIELD_NUMBER: _ClassVar[int]
    alpha: float
    fusion_type: HybridSearchParams.FusionType
    properties: _containers.RepeatedScalarFieldContainer[str]
    query: str
    vector: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, query: _Optional[str] = ..., properties: _Optional[_Iterable[str]] = ..., vector: _Optional[_Iterable[float]] = ..., alpha: _Optional[float] = ..., fusion_type: _Optional[_Union[HybridSearchParams.FusionType, str]] = ...) -> None: ...

class NearObjectParams(_message.Message):
    __slots__ = ["certainty", "distance", "id"]
    CERTAINTY_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    certainty: float
    distance: float
    id: str
    def __init__(self, id: _Optional[str] = ..., certainty: _Optional[float] = ..., distance: _Optional[float] = ...) -> None: ...

class NearVectorParams(_message.Message):
    __slots__ = ["certainty", "distance", "vector"]
    CERTAINTY_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    VECTOR_FIELD_NUMBER: _ClassVar[int]
    certainty: float
    distance: float
    vector: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, vector: _Optional[_Iterable[float]] = ..., certainty: _Optional[float] = ..., distance: _Optional[float] = ...) -> None: ...

class Properties(_message.Message):
    __slots__ = ["non_ref_properties", "ref_properties"]
    NON_REF_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    REF_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    non_ref_properties: _containers.RepeatedScalarFieldContainer[str]
    ref_properties: _containers.RepeatedCompositeFieldContainer[RefProperties]
    def __init__(self, non_ref_properties: _Optional[_Iterable[str]] = ..., ref_properties: _Optional[_Iterable[_Union[RefProperties, _Mapping]]] = ...) -> None: ...

class RefProperties(_message.Message):
    __slots__ = ["linked_properties", "metadata", "reference_property", "which_collection"]
    LINKED_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    REFERENCE_PROPERTY_FIELD_NUMBER: _ClassVar[int]
    WHICH_COLLECTION_FIELD_NUMBER: _ClassVar[int]
    linked_properties: Properties
    metadata: AdditionalProperties
    reference_property: str
    which_collection: str
    def __init__(self, reference_property: _Optional[str] = ..., linked_properties: _Optional[_Union[Properties, _Mapping]] = ..., metadata: _Optional[_Union[AdditionalProperties, _Mapping]] = ..., which_collection: _Optional[str] = ...) -> None: ...

class ResultAdditionalProps(_message.Message):
    __slots__ = ["certainty", "certainty_present", "creation_time_unix", "creation_time_unix_present", "distance", "distance_present", "explain_score", "explain_score_present", "id", "last_update_time_unix", "last_update_time_unix_present", "score", "score_present", "vector"]
    CERTAINTY_FIELD_NUMBER: _ClassVar[int]
    CERTAINTY_PRESENT_FIELD_NUMBER: _ClassVar[int]
    CREATION_TIME_UNIX_FIELD_NUMBER: _ClassVar[int]
    CREATION_TIME_UNIX_PRESENT_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_PRESENT_FIELD_NUMBER: _ClassVar[int]
    EXPLAIN_SCORE_FIELD_NUMBER: _ClassVar[int]
    EXPLAIN_SCORE_PRESENT_FIELD_NUMBER: _ClassVar[int]
    ID_FIELD_NUMBER: _ClassVar[int]
    LAST_UPDATE_TIME_UNIX_FIELD_NUMBER: _ClassVar[int]
    LAST_UPDATE_TIME_UNIX_PRESENT_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    SCORE_PRESENT_FIELD_NUMBER: _ClassVar[int]
    VECTOR_FIELD_NUMBER: _ClassVar[int]
    certainty: float
    certainty_present: bool
    creation_time_unix: int
    creation_time_unix_present: bool
    distance: float
    distance_present: bool
    explain_score: str
    explain_score_present: bool
    id: str
    last_update_time_unix: int
    last_update_time_unix_present: bool
    score: float
    score_present: bool
    vector: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, id: _Optional[str] = ..., vector: _Optional[_Iterable[float]] = ..., creation_time_unix: _Optional[int] = ..., creation_time_unix_present: bool = ..., last_update_time_unix: _Optional[int] = ..., last_update_time_unix_present: bool = ..., distance: _Optional[float] = ..., distance_present: bool = ..., certainty: _Optional[float] = ..., certainty_present: bool = ..., score: _Optional[float] = ..., score_present: bool = ..., explain_score: _Optional[str] = ..., explain_score_present: bool = ...) -> None: ...

class ResultProperties(_message.Message):
    __slots__ = ["class_name", "metadata", "non_ref_properties", "ref_props"]
    CLASS_NAME_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    NON_REF_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    REF_PROPS_FIELD_NUMBER: _ClassVar[int]
    class_name: str
    metadata: ResultAdditionalProps
    non_ref_properties: _struct_pb2.Struct
    ref_props: _containers.RepeatedCompositeFieldContainer[ReturnRefProperties]
    def __init__(self, non_ref_properties: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ..., ref_props: _Optional[_Iterable[_Union[ReturnRefProperties, _Mapping]]] = ..., class_name: _Optional[str] = ..., metadata: _Optional[_Union[ResultAdditionalProps, _Mapping]] = ...) -> None: ...

class ReturnRefProperties(_message.Message):
    __slots__ = ["prop_name", "properties"]
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    PROP_NAME_FIELD_NUMBER: _ClassVar[int]
    prop_name: str
    properties: _containers.RepeatedCompositeFieldContainer[ResultProperties]
    def __init__(self, properties: _Optional[_Iterable[_Union[ResultProperties, _Mapping]]] = ..., prop_name: _Optional[str] = ...) -> None: ...

class SearchReply(_message.Message):
    __slots__ = ["results", "took"]
    RESULTS_FIELD_NUMBER: _ClassVar[int]
    TOOK_FIELD_NUMBER: _ClassVar[int]
    results: _containers.RepeatedCompositeFieldContainer[SearchResult]
    took: float
    def __init__(self, results: _Optional[_Iterable[_Union[SearchResult, _Mapping]]] = ..., took: _Optional[float] = ...) -> None: ...

class SearchRequest(_message.Message):
    __slots__ = ["additional_properties", "after", "autocut", "bm25_search", "class_name", "filters", "hybrid_search", "limit", "near_object", "near_vector", "offset", "properties", "tenant"]
    ADDITIONAL_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    AFTER_FIELD_NUMBER: _ClassVar[int]
    AUTOCUT_FIELD_NUMBER: _ClassVar[int]
    BM25_SEARCH_FIELD_NUMBER: _ClassVar[int]
    CLASS_NAME_FIELD_NUMBER: _ClassVar[int]
    FILTERS_FIELD_NUMBER: _ClassVar[int]
    HYBRID_SEARCH_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    NEAR_OBJECT_FIELD_NUMBER: _ClassVar[int]
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
    near_vector: NearVectorParams
    offset: int
    properties: Properties
    tenant: str
    def __init__(self, class_name: _Optional[str] = ..., limit: _Optional[int] = ..., additional_properties: _Optional[_Union[AdditionalProperties, _Mapping]] = ..., near_vector: _Optional[_Union[NearVectorParams, _Mapping]] = ..., near_object: _Optional[_Union[NearObjectParams, _Mapping]] = ..., properties: _Optional[_Union[Properties, _Mapping]] = ..., hybrid_search: _Optional[_Union[HybridSearchParams, _Mapping]] = ..., bm25_search: _Optional[_Union[BM25SearchParams, _Mapping]] = ..., offset: _Optional[int] = ..., autocut: _Optional[int] = ..., after: _Optional[str] = ..., tenant: _Optional[str] = ..., filters: _Optional[_Union[Filters, _Mapping]] = ...) -> None: ...

class SearchResult(_message.Message):
    __slots__ = ["additional_properties", "properties"]
    ADDITIONAL_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    additional_properties: ResultAdditionalProps
    properties: ResultProperties
    def __init__(self, properties: _Optional[_Union[ResultProperties, _Mapping]] = ..., additional_properties: _Optional[_Union[ResultAdditionalProps, _Mapping]] = ...) -> None: ...
