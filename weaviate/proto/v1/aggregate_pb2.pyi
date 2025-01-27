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

class AggregateRequest(_message.Message):
    __slots__ = ("collection", "meta_count", "object_limit", "tenant")
    COLLECTION_FIELD_NUMBER: _ClassVar[int]
    META_COUNT_FIELD_NUMBER: _ClassVar[int]
    OBJECT_LIMIT_FIELD_NUMBER: _ClassVar[int]
    TENANT_FIELD_NUMBER: _ClassVar[int]
    collection: str
    meta_count: bool
    object_limit: int
    tenant: str
    def __init__(
        self,
        collection: _Optional[str] = ...,
        meta_count: bool = ...,
        object_limit: _Optional[int] = ...,
        tenant: _Optional[str] = ...,
    ) -> None: ...

class AggregateReply(_message.Message):
    __slots__ = ("took", "result")
    TOOK_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    took: float
    result: AggregateResult
    def __init__(
        self,
        took: _Optional[float] = ...,
        result: _Optional[_Union[AggregateResult, _Mapping]] = ...,
    ) -> None: ...

class AggregateResult(_message.Message):
    __slots__ = ("groups",)
    GROUPS_FIELD_NUMBER: _ClassVar[int]
    groups: _containers.RepeatedCompositeFieldContainer[AggregateGroupResult]
    def __init__(
        self, groups: _Optional[_Iterable[_Union[AggregateGroupResult, _Mapping]]] = ...
    ) -> None: ...

class AggregateGroupResult(_message.Message):
    __slots__ = ("count",)
    COUNT_FIELD_NUMBER: _ClassVar[int]
    count: int
    def __init__(self, count: _Optional[int] = ...) -> None: ...
