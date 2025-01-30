from google.protobuf import struct_pb2 as _struct_pb2
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

class ConsistencyLevel(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CONSISTENCY_LEVEL_UNSPECIFIED: _ClassVar[ConsistencyLevel]
    CONSISTENCY_LEVEL_ONE: _ClassVar[ConsistencyLevel]
    CONSISTENCY_LEVEL_QUORUM: _ClassVar[ConsistencyLevel]
    CONSISTENCY_LEVEL_ALL: _ClassVar[ConsistencyLevel]

CONSISTENCY_LEVEL_UNSPECIFIED: ConsistencyLevel
CONSISTENCY_LEVEL_ONE: ConsistencyLevel
CONSISTENCY_LEVEL_QUORUM: ConsistencyLevel
CONSISTENCY_LEVEL_ALL: ConsistencyLevel

class NumberArrayProperties(_message.Message):
    __slots__ = ("values", "prop_name", "values_bytes")
    VALUES_FIELD_NUMBER: _ClassVar[int]
    PROP_NAME_FIELD_NUMBER: _ClassVar[int]
    VALUES_BYTES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[float]
    prop_name: str
    values_bytes: bytes
    def __init__(
        self,
        values: _Optional[_Iterable[float]] = ...,
        prop_name: _Optional[str] = ...,
        values_bytes: _Optional[bytes] = ...,
    ) -> None: ...

class IntArrayProperties(_message.Message):
    __slots__ = ("values", "prop_name")
    VALUES_FIELD_NUMBER: _ClassVar[int]
    PROP_NAME_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[int]
    prop_name: str
    def __init__(
        self, values: _Optional[_Iterable[int]] = ..., prop_name: _Optional[str] = ...
    ) -> None: ...

class TextArrayProperties(_message.Message):
    __slots__ = ("values", "prop_name")
    VALUES_FIELD_NUMBER: _ClassVar[int]
    PROP_NAME_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[str]
    prop_name: str
    def __init__(
        self, values: _Optional[_Iterable[str]] = ..., prop_name: _Optional[str] = ...
    ) -> None: ...

class BooleanArrayProperties(_message.Message):
    __slots__ = ("values", "prop_name")
    VALUES_FIELD_NUMBER: _ClassVar[int]
    PROP_NAME_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[bool]
    prop_name: str
    def __init__(
        self, values: _Optional[_Iterable[bool]] = ..., prop_name: _Optional[str] = ...
    ) -> None: ...

class ObjectPropertiesValue(_message.Message):
    __slots__ = (
        "non_ref_properties",
        "number_array_properties",
        "int_array_properties",
        "text_array_properties",
        "boolean_array_properties",
        "object_properties",
        "object_array_properties",
        "empty_list_props",
    )
    NON_REF_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    NUMBER_ARRAY_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    INT_ARRAY_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    TEXT_ARRAY_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    BOOLEAN_ARRAY_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    OBJECT_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ARRAY_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    EMPTY_LIST_PROPS_FIELD_NUMBER: _ClassVar[int]
    non_ref_properties: _struct_pb2.Struct
    number_array_properties: _containers.RepeatedCompositeFieldContainer[NumberArrayProperties]
    int_array_properties: _containers.RepeatedCompositeFieldContainer[IntArrayProperties]
    text_array_properties: _containers.RepeatedCompositeFieldContainer[TextArrayProperties]
    boolean_array_properties: _containers.RepeatedCompositeFieldContainer[BooleanArrayProperties]
    object_properties: _containers.RepeatedCompositeFieldContainer[ObjectProperties]
    object_array_properties: _containers.RepeatedCompositeFieldContainer[ObjectArrayProperties]
    empty_list_props: _containers.RepeatedScalarFieldContainer[str]
    def __init__(
        self,
        non_ref_properties: _Optional[_Union[_struct_pb2.Struct, _Mapping]] = ...,
        number_array_properties: _Optional[
            _Iterable[_Union[NumberArrayProperties, _Mapping]]
        ] = ...,
        int_array_properties: _Optional[_Iterable[_Union[IntArrayProperties, _Mapping]]] = ...,
        text_array_properties: _Optional[_Iterable[_Union[TextArrayProperties, _Mapping]]] = ...,
        boolean_array_properties: _Optional[
            _Iterable[_Union[BooleanArrayProperties, _Mapping]]
        ] = ...,
        object_properties: _Optional[_Iterable[_Union[ObjectProperties, _Mapping]]] = ...,
        object_array_properties: _Optional[
            _Iterable[_Union[ObjectArrayProperties, _Mapping]]
        ] = ...,
        empty_list_props: _Optional[_Iterable[str]] = ...,
    ) -> None: ...

class ObjectArrayProperties(_message.Message):
    __slots__ = ("values", "prop_name")
    VALUES_FIELD_NUMBER: _ClassVar[int]
    PROP_NAME_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedCompositeFieldContainer[ObjectPropertiesValue]
    prop_name: str
    def __init__(
        self,
        values: _Optional[_Iterable[_Union[ObjectPropertiesValue, _Mapping]]] = ...,
        prop_name: _Optional[str] = ...,
    ) -> None: ...

class ObjectProperties(_message.Message):
    __slots__ = ("value", "prop_name")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    PROP_NAME_FIELD_NUMBER: _ClassVar[int]
    value: ObjectPropertiesValue
    prop_name: str
    def __init__(
        self,
        value: _Optional[_Union[ObjectPropertiesValue, _Mapping]] = ...,
        prop_name: _Optional[str] = ...,
    ) -> None: ...

class TextArray(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, values: _Optional[_Iterable[str]] = ...) -> None: ...

class IntArray(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, values: _Optional[_Iterable[int]] = ...) -> None: ...

class NumberArray(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, values: _Optional[_Iterable[float]] = ...) -> None: ...

class BooleanArray(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[bool]
    def __init__(self, values: _Optional[_Iterable[bool]] = ...) -> None: ...

class Filters(_message.Message):
    __slots__ = (
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
        "value_geo",
        "target",
    )

    class Operator(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
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
    VALUE_GEO_FIELD_NUMBER: _ClassVar[int]
    TARGET_FIELD_NUMBER: _ClassVar[int]
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
    value_geo: GeoCoordinatesFilter
    target: FilterTarget
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
        value_geo: _Optional[_Union[GeoCoordinatesFilter, _Mapping]] = ...,
        target: _Optional[_Union[FilterTarget, _Mapping]] = ...,
    ) -> None: ...

class FilterReferenceSingleTarget(_message.Message):
    __slots__ = ("on", "target")
    ON_FIELD_NUMBER: _ClassVar[int]
    TARGET_FIELD_NUMBER: _ClassVar[int]
    on: str
    target: FilterTarget
    def __init__(
        self, on: _Optional[str] = ..., target: _Optional[_Union[FilterTarget, _Mapping]] = ...
    ) -> None: ...

class FilterReferenceMultiTarget(_message.Message):
    __slots__ = ("on", "target", "target_collection")
    ON_FIELD_NUMBER: _ClassVar[int]
    TARGET_FIELD_NUMBER: _ClassVar[int]
    TARGET_COLLECTION_FIELD_NUMBER: _ClassVar[int]
    on: str
    target: FilterTarget
    target_collection: str
    def __init__(
        self,
        on: _Optional[str] = ...,
        target: _Optional[_Union[FilterTarget, _Mapping]] = ...,
        target_collection: _Optional[str] = ...,
    ) -> None: ...

class FilterReferenceCount(_message.Message):
    __slots__ = ("on",)
    ON_FIELD_NUMBER: _ClassVar[int]
    on: str
    def __init__(self, on: _Optional[str] = ...) -> None: ...

class FilterTarget(_message.Message):
    __slots__ = ("property", "single_target", "multi_target", "count")
    PROPERTY_FIELD_NUMBER: _ClassVar[int]
    SINGLE_TARGET_FIELD_NUMBER: _ClassVar[int]
    MULTI_TARGET_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    property: str
    single_target: FilterReferenceSingleTarget
    multi_target: FilterReferenceMultiTarget
    count: FilterReferenceCount
    def __init__(
        self,
        property: _Optional[str] = ...,
        single_target: _Optional[_Union[FilterReferenceSingleTarget, _Mapping]] = ...,
        multi_target: _Optional[_Union[FilterReferenceMultiTarget, _Mapping]] = ...,
        count: _Optional[_Union[FilterReferenceCount, _Mapping]] = ...,
    ) -> None: ...

class GeoCoordinatesFilter(_message.Message):
    __slots__ = ("latitude", "longitude", "distance")
    LATITUDE_FIELD_NUMBER: _ClassVar[int]
    LONGITUDE_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    latitude: float
    longitude: float
    distance: float
    def __init__(
        self,
        latitude: _Optional[float] = ...,
        longitude: _Optional[float] = ...,
        distance: _Optional[float] = ...,
    ) -> None: ...

class Vectors(_message.Message):
    __slots__ = ("name", "index", "vector_bytes", "type")

    class VectorType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        VECTOR_TYPE_UNSPECIFIED: _ClassVar[Vectors.VectorType]
        VECTOR_TYPE_SINGLE_FP32: _ClassVar[Vectors.VectorType]
        VECTOR_TYPE_MULTI_FP32: _ClassVar[Vectors.VectorType]

    VECTOR_TYPE_UNSPECIFIED: Vectors.VectorType
    VECTOR_TYPE_SINGLE_FP32: Vectors.VectorType
    VECTOR_TYPE_MULTI_FP32: Vectors.VectorType
    NAME_FIELD_NUMBER: _ClassVar[int]
    INDEX_FIELD_NUMBER: _ClassVar[int]
    VECTOR_BYTES_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    name: str
    index: int
    vector_bytes: bytes
    type: Vectors.VectorType
    def __init__(
        self,
        name: _Optional[str] = ...,
        index: _Optional[int] = ...,
        vector_bytes: _Optional[bytes] = ...,
        type: _Optional[_Union[Vectors.VectorType, str]] = ...,
    ) -> None: ...
