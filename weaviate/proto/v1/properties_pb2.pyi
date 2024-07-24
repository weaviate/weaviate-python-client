from google.protobuf import struct_pb2 as _struct_pb2
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

class Properties(_message.Message):
    __slots__ = ("fields",)

    class FieldsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: Value
        def __init__(
            self, key: _Optional[str] = ..., value: _Optional[_Union[Value, _Mapping]] = ...
        ) -> None: ...
    FIELDS_FIELD_NUMBER: _ClassVar[int]
    fields: _containers.MessageMap[str, Value]
    def __init__(self, fields: _Optional[_Mapping[str, Value]] = ...) -> None: ...

class Value(_message.Message):
    __slots__ = (
        "number_value",
        "string_value",
        "bool_value",
        "object_value",
        "list_value",
        "date_value",
        "uuid_value",
        "int_value",
        "geo_value",
        "blob_value",
        "phone_value",
        "null_value",
        "text_value",
    )
    NUMBER_VALUE_FIELD_NUMBER: _ClassVar[int]
    STRING_VALUE_FIELD_NUMBER: _ClassVar[int]
    BOOL_VALUE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_VALUE_FIELD_NUMBER: _ClassVar[int]
    LIST_VALUE_FIELD_NUMBER: _ClassVar[int]
    DATE_VALUE_FIELD_NUMBER: _ClassVar[int]
    UUID_VALUE_FIELD_NUMBER: _ClassVar[int]
    INT_VALUE_FIELD_NUMBER: _ClassVar[int]
    GEO_VALUE_FIELD_NUMBER: _ClassVar[int]
    BLOB_VALUE_FIELD_NUMBER: _ClassVar[int]
    PHONE_VALUE_FIELD_NUMBER: _ClassVar[int]
    NULL_VALUE_FIELD_NUMBER: _ClassVar[int]
    TEXT_VALUE_FIELD_NUMBER: _ClassVar[int]
    number_value: float
    string_value: str
    bool_value: bool
    object_value: Properties
    list_value: ListValue
    date_value: str
    uuid_value: str
    int_value: int
    geo_value: GeoCoordinate
    blob_value: str
    phone_value: PhoneNumber
    null_value: _struct_pb2.NullValue
    text_value: str
    def __init__(
        self,
        number_value: _Optional[float] = ...,
        string_value: _Optional[str] = ...,
        bool_value: bool = ...,
        object_value: _Optional[_Union[Properties, _Mapping]] = ...,
        list_value: _Optional[_Union[ListValue, _Mapping]] = ...,
        date_value: _Optional[str] = ...,
        uuid_value: _Optional[str] = ...,
        int_value: _Optional[int] = ...,
        geo_value: _Optional[_Union[GeoCoordinate, _Mapping]] = ...,
        blob_value: _Optional[str] = ...,
        phone_value: _Optional[_Union[PhoneNumber, _Mapping]] = ...,
        null_value: _Optional[_Union[_struct_pb2.NullValue, str]] = ...,
        text_value: _Optional[str] = ...,
    ) -> None: ...

class ListValue(_message.Message):
    __slots__ = (
        "values",
        "number_values",
        "bool_values",
        "object_values",
        "date_values",
        "uuid_values",
        "int_values",
        "text_values",
    )
    VALUES_FIELD_NUMBER: _ClassVar[int]
    NUMBER_VALUES_FIELD_NUMBER: _ClassVar[int]
    BOOL_VALUES_FIELD_NUMBER: _ClassVar[int]
    OBJECT_VALUES_FIELD_NUMBER: _ClassVar[int]
    DATE_VALUES_FIELD_NUMBER: _ClassVar[int]
    UUID_VALUES_FIELD_NUMBER: _ClassVar[int]
    INT_VALUES_FIELD_NUMBER: _ClassVar[int]
    TEXT_VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedCompositeFieldContainer[Value]
    number_values: NumberValues
    bool_values: BoolValues
    object_values: ObjectValues
    date_values: DateValues
    uuid_values: UuidValues
    int_values: IntValues
    text_values: TextValues
    def __init__(
        self,
        values: _Optional[_Iterable[_Union[Value, _Mapping]]] = ...,
        number_values: _Optional[_Union[NumberValues, _Mapping]] = ...,
        bool_values: _Optional[_Union[BoolValues, _Mapping]] = ...,
        object_values: _Optional[_Union[ObjectValues, _Mapping]] = ...,
        date_values: _Optional[_Union[DateValues, _Mapping]] = ...,
        uuid_values: _Optional[_Union[UuidValues, _Mapping]] = ...,
        int_values: _Optional[_Union[IntValues, _Mapping]] = ...,
        text_values: _Optional[_Union[TextValues, _Mapping]] = ...,
    ) -> None: ...

class NumberValues(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: bytes
    def __init__(self, values: _Optional[bytes] = ...) -> None: ...

class TextValues(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, values: _Optional[_Iterable[str]] = ...) -> None: ...

class BoolValues(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[bool]
    def __init__(self, values: _Optional[_Iterable[bool]] = ...) -> None: ...

class ObjectValues(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedCompositeFieldContainer[Properties]
    def __init__(
        self, values: _Optional[_Iterable[_Union[Properties, _Mapping]]] = ...
    ) -> None: ...

class DateValues(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, values: _Optional[_Iterable[str]] = ...) -> None: ...

class UuidValues(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, values: _Optional[_Iterable[str]] = ...) -> None: ...

class IntValues(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: bytes
    def __init__(self, values: _Optional[bytes] = ...) -> None: ...

class GeoCoordinate(_message.Message):
    __slots__ = ("longitude", "latitude")
    LONGITUDE_FIELD_NUMBER: _ClassVar[int]
    LATITUDE_FIELD_NUMBER: _ClassVar[int]
    longitude: float
    latitude: float
    def __init__(
        self, longitude: _Optional[float] = ..., latitude: _Optional[float] = ...
    ) -> None: ...

class PhoneNumber(_message.Message):
    __slots__ = (
        "country_code",
        "default_country",
        "input",
        "international_formatted",
        "national",
        "national_formatted",
        "valid",
    )
    COUNTRY_CODE_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_COUNTRY_FIELD_NUMBER: _ClassVar[int]
    INPUT_FIELD_NUMBER: _ClassVar[int]
    INTERNATIONAL_FORMATTED_FIELD_NUMBER: _ClassVar[int]
    NATIONAL_FIELD_NUMBER: _ClassVar[int]
    NATIONAL_FORMATTED_FIELD_NUMBER: _ClassVar[int]
    VALID_FIELD_NUMBER: _ClassVar[int]
    country_code: int
    default_country: str
    input: str
    international_formatted: str
    national: int
    national_formatted: str
    valid: bool
    def __init__(
        self,
        country_code: _Optional[int] = ...,
        default_country: _Optional[str] = ...,
        input: _Optional[str] = ...,
        international_formatted: _Optional[str] = ...,
        national: _Optional[int] = ...,
        national_formatted: _Optional[str] = ...,
        valid: bool = ...,
    ) -> None: ...
