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

class BatchDeleteRequest(_message.Message):
    __slots__ = ("collection", "filters", "verbose", "dry_run", "consistency_level", "tenant")
    COLLECTION_FIELD_NUMBER: _ClassVar[int]
    FILTERS_FIELD_NUMBER: _ClassVar[int]
    VERBOSE_FIELD_NUMBER: _ClassVar[int]
    DRY_RUN_FIELD_NUMBER: _ClassVar[int]
    CONSISTENCY_LEVEL_FIELD_NUMBER: _ClassVar[int]
    TENANT_FIELD_NUMBER: _ClassVar[int]
    collection: str
    filters: _base_pb2.Filters
    verbose: bool
    dry_run: bool
    consistency_level: _base_pb2.ConsistencyLevel
    tenant: str
    def __init__(
        self,
        collection: _Optional[str] = ...,
        filters: _Optional[_Union[_base_pb2.Filters, _Mapping]] = ...,
        verbose: bool = ...,
        dry_run: bool = ...,
        consistency_level: _Optional[_Union[_base_pb2.ConsistencyLevel, str]] = ...,
        tenant: _Optional[str] = ...,
    ) -> None: ...

class BatchDeleteReply(_message.Message):
    __slots__ = ("took", "failed", "matches", "successful", "objects")
    TOOK_FIELD_NUMBER: _ClassVar[int]
    FAILED_FIELD_NUMBER: _ClassVar[int]
    MATCHES_FIELD_NUMBER: _ClassVar[int]
    SUCCESSFUL_FIELD_NUMBER: _ClassVar[int]
    OBJECTS_FIELD_NUMBER: _ClassVar[int]
    took: float
    failed: int
    matches: int
    successful: int
    objects: _containers.RepeatedCompositeFieldContainer[BatchDeleteObject]
    def __init__(
        self,
        took: _Optional[float] = ...,
        failed: _Optional[int] = ...,
        matches: _Optional[int] = ...,
        successful: _Optional[int] = ...,
        objects: _Optional[_Iterable[_Union[BatchDeleteObject, _Mapping]]] = ...,
    ) -> None: ...

class BatchDeleteObject(_message.Message):
    __slots__ = ("uuid", "successful", "error")
    UUID_FIELD_NUMBER: _ClassVar[int]
    SUCCESSFUL_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    uuid: bytes
    successful: bool
    error: str
    def __init__(
        self, uuid: _Optional[bytes] = ..., successful: bool = ..., error: _Optional[str] = ...
    ) -> None: ...
