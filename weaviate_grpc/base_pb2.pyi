from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Optional as _Optional

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
    def __init__(self, values: _Optional[_Iterable[float]] = ..., prop_name: _Optional[str] = ...) -> None: ...

class IntArrayProperties(_message.Message):
    __slots__ = ["values", "prop_name"]
    VALUES_FIELD_NUMBER: _ClassVar[int]
    PROP_NAME_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[int]
    prop_name: str
    def __init__(self, values: _Optional[_Iterable[int]] = ..., prop_name: _Optional[str] = ...) -> None: ...

class TextArrayProperties(_message.Message):
    __slots__ = ["values", "prop_name"]
    VALUES_FIELD_NUMBER: _ClassVar[int]
    PROP_NAME_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[str]
    prop_name: str
    def __init__(self, values: _Optional[_Iterable[str]] = ..., prop_name: _Optional[str] = ...) -> None: ...

class BooleanArrayProperties(_message.Message):
    __slots__ = ["values", "prop_name"]
    VALUES_FIELD_NUMBER: _ClassVar[int]
    PROP_NAME_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[bool]
    prop_name: str
    def __init__(self, values: _Optional[_Iterable[bool]] = ..., prop_name: _Optional[str] = ...) -> None: ...
