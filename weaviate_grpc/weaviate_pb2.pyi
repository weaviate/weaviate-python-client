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

class NearObjectParams(_message.Message):
    __slots__ = ["id"]
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class NearVectorParams(_message.Message):
    __slots__ = ["vector"]
    VECTOR_FIELD_NUMBER: _ClassVar[int]
    vector: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, vector: _Optional[_Iterable[float]] = ...) -> None: ...

class SearchReply(_message.Message):
    __slots__ = ["results", "took"]
    RESULTS_FIELD_NUMBER: _ClassVar[int]
    TOOK_FIELD_NUMBER: _ClassVar[int]
    results: _containers.RepeatedCompositeFieldContainer[SearchResult]
    took: float
    def __init__(
        self,
        results: _Optional[_Iterable[_Union[SearchResult, _Mapping]]] = ...,
        took: _Optional[float] = ...,
    ) -> None: ...

class SearchRequest(_message.Message):
    __slots__ = ["className", "limit", "nearObject", "nearVector"]
    CLASSNAME_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    NEAROBJECT_FIELD_NUMBER: _ClassVar[int]
    NEARVECTOR_FIELD_NUMBER: _ClassVar[int]
    className: str
    limit: int
    nearObject: NearObjectParams
    nearVector: NearVectorParams
    def __init__(
        self,
        className: _Optional[str] = ...,
        limit: _Optional[int] = ...,
        nearVector: _Optional[_Union[NearVectorParams, _Mapping]] = ...,
        nearObject: _Optional[_Union[NearObjectParams, _Mapping]] = ...,
    ) -> None: ...

class SearchResult(_message.Message):
    __slots__ = ["id"]
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...
