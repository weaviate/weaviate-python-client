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
    __slots__ = []
    CONSISTENCY_LEVEL_UNSPECIFIED: _ClassVar[ConsistencyLevel]
    CONSISTENCY_LEVEL_ONE: _ClassVar[ConsistencyLevel]
    CONSISTENCY_LEVEL_QUORUM: _ClassVar[ConsistencyLevel]
    CONSISTENCY_LEVEL_ALL: _ClassVar[ConsistencyLevel]

CONSISTENCY_LEVEL_UNSPECIFIED: ConsistencyLevel
CONSISTENCY_LEVEL_ONE: ConsistencyLevel
CONSISTENCY_LEVEL_QUORUM: ConsistencyLevel
CONSISTENCY_LEVEL_ALL: ConsistencyLevel

class NumberArrayProperties(_message.Message):
    __slots__ = ["values", "prop_name"]
    VALUES_FIELD_NUMBER: _ClassVar[int]
    PROP_NAME_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[float]
    prop_name: str
    def __init__(
        self, values: _Optional[_Iterable[float]] = ..., prop_name: _Optional[str] = ...
    ) -> None: ...

class IntArrayProperties(_message.Message):
    __slots__ = ["values", "prop_name"]
    VALUES_FIELD_NUMBER: _ClassVar[int]
    PROP_NAME_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[int]
    prop_name: str
    def __init__(
        self, values: _Optional[_Iterable[int]] = ..., prop_name: _Optional[str] = ...
    ) -> None: ...

class TextArrayProperties(_message.Message):
    __slots__ = ["values", "prop_name"]
    VALUES_FIELD_NUMBER: _ClassVar[int]
    PROP_NAME_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[str]
    prop_name: str
    def __init__(
        self, values: _Optional[_Iterable[str]] = ..., prop_name: _Optional[str] = ...
    ) -> None: ...

class BooleanArrayProperties(_message.Message):
    __slots__ = ["values", "prop_name"]
    VALUES_FIELD_NUMBER: _ClassVar[int]
    PROP_NAME_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[bool]
    prop_name: str
    def __init__(
        self, values: _Optional[_Iterable[bool]] = ..., prop_name: _Optional[str] = ...
    ) -> None: ...

class ObjectPropertiesValue(_message.Message):
    __slots__ = [
        "non_ref_properties",
        "number_array_properties",
        "int_array_properties",
        "text_array_properties",
        "boolean_array_properties",
        "object_properties",
        "object_array_properties",
    ]
    NON_REF_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    NUMBER_ARRAY_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    INT_ARRAY_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    TEXT_ARRAY_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    BOOLEAN_ARRAY_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    OBJECT_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    OBJECT_ARRAY_PROPERTIES_FIELD_NUMBER: _ClassVar[int]
    non_ref_properties: _struct_pb2.Struct
    number_array_properties: _containers.RepeatedCompositeFieldContainer[NumberArrayProperties]
    int_array_properties: _containers.RepeatedCompositeFieldContainer[IntArrayProperties]
    text_array_properties: _containers.RepeatedCompositeFieldContainer[TextArrayProperties]
    boolean_array_properties: _containers.RepeatedCompositeFieldContainer[BooleanArrayProperties]
    object_properties: _containers.RepeatedCompositeFieldContainer[ObjectProperties]
    object_array_properties: _containers.RepeatedCompositeFieldContainer[ObjectArrayProperties]
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
    ) -> None: ...

class ObjectArrayProperties(_message.Message):
    __slots__ = ["values", "prop_name"]
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
    __slots__ = ["value", "prop_name"]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    PROP_NAME_FIELD_NUMBER: _ClassVar[int]
    value: ObjectPropertiesValue
    prop_name: str
    def __init__(
        self,
        value: _Optional[_Union[ObjectPropertiesValue, _Mapping]] = ...,
        prop_name: _Optional[str] = ...,
    ) -> None: ...
