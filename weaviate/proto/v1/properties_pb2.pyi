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
    __slots__ = ["fields"]

    class FieldsEntry(_message.Message):
        __slots__ = ["key", "value"]
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
    __slots__ = [
        "number_value",
        "string_value",
        "bool_value",
        "object_value",
        "list_value",
        "date_value",
        "uuid_value",
        "int_value",
        "geo_value",
    ]
    NUMBER_VALUE_FIELD_NUMBER: _ClassVar[int]
    STRING_VALUE_FIELD_NUMBER: _ClassVar[int]
    BOOL_VALUE_FIELD_NUMBER: _ClassVar[int]
    OBJECT_VALUE_FIELD_NUMBER: _ClassVar[int]
    LIST_VALUE_FIELD_NUMBER: _ClassVar[int]
    DATE_VALUE_FIELD_NUMBER: _ClassVar[int]
    UUID_VALUE_FIELD_NUMBER: _ClassVar[int]
    INT_VALUE_FIELD_NUMBER: _ClassVar[int]
    GEO_VALUE_FIELD_NUMBER: _ClassVar[int]
    number_value: float
    string_value: str
    bool_value: bool
    object_value: Properties
    list_value: ListValue
    date_value: str
    uuid_value: str
    int_value: int
    geo_value: GeoCoordinate
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
    ) -> None: ...

class ListValue(_message.Message):
    __slots__ = ["values"]
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedCompositeFieldContainer[Value]
    def __init__(self, values: _Optional[_Iterable[_Union[Value, _Mapping]]] = ...) -> None: ...

class GeoCoordinate(_message.Message):
    __slots__ = ["longitude", "latitude"]
    LONGITUDE_FIELD_NUMBER: _ClassVar[int]
    LATITUDE_FIELD_NUMBER: _ClassVar[int]
    longitude: float
    latitude: float
    def __init__(
        self, longitude: _Optional[float] = ..., latitude: _Optional[float] = ...
    ) -> None: ...
