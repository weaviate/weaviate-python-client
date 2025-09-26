from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class WeaviateHealthCheckRequest(_message.Message):
    __slots__ = ["service"]
    SERVICE_FIELD_NUMBER: _ClassVar[int]
    service: str
    def __init__(self, service: _Optional[str] = ...) -> None: ...

class WeaviateHealthCheckResponse(_message.Message):
    __slots__ = ["status"]
    class ServingStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = []
        UNKNOWN: _ClassVar[WeaviateHealthCheckResponse.ServingStatus]
        SERVING: _ClassVar[WeaviateHealthCheckResponse.ServingStatus]
        NOT_SERVING: _ClassVar[WeaviateHealthCheckResponse.ServingStatus]
    UNKNOWN: WeaviateHealthCheckResponse.ServingStatus
    SERVING: WeaviateHealthCheckResponse.ServingStatus
    NOT_SERVING: WeaviateHealthCheckResponse.ServingStatus
    STATUS_FIELD_NUMBER: _ClassVar[int]
    status: WeaviateHealthCheckResponse.ServingStatus
    def __init__(self, status: _Optional[_Union[WeaviateHealthCheckResponse.ServingStatus, str]] = ...) -> None: ...
