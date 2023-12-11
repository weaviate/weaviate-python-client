from weaviate.proto.v1 import base_pb2 as _base_pb2
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
    __slots__ = ["collection", "tenant", "number_of_objects"]
    COLLECTION_FIELD_NUMBER: _ClassVar[int]
    TENANT_FIELD_NUMBER: _ClassVar[int]
    NUMBER_OF_OBJECTS_FIELD_NUMBER: _ClassVar[int]
    collection: str
    tenant: str
    number_of_objects: bool
    def __init__(
        self,
        collection: _Optional[str] = ...,
        tenant: _Optional[str] = ...,
        number_of_objects: bool = ...,
    ) -> None: ...

class AggregateReply(_message.Message):
    __slots__ = ["took", "results"]
    TOOK_FIELD_NUMBER: _ClassVar[int]
    RESULTS_FIELD_NUMBER: _ClassVar[int]
    took: float
    results: _containers.RepeatedCompositeFieldContainer[AggregateResult]
    def __init__(
        self,
        took: _Optional[float] = ...,
        results: _Optional[_Iterable[_Union[AggregateResult, _Mapping]]] = ...,
    ) -> None: ...

class AggregateResult(_message.Message):
    __slots__ = ["number_of_objects"]
    NUMBER_OF_OBJECTS_FIELD_NUMBER: _ClassVar[int]
    number_of_objects: int
    def __init__(self, number_of_objects: _Optional[int] = ...) -> None: ...
