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

class TenantActivityStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TENANT_ACTIVITY_STATUS_UNSPECIFIED: _ClassVar[TenantActivityStatus]
    TENANT_ACTIVITY_STATUS_HOT: _ClassVar[TenantActivityStatus]
    TENANT_ACTIVITY_STATUS_COLD: _ClassVar[TenantActivityStatus]
    TENANT_ACTIVITY_STATUS_FROZEN: _ClassVar[TenantActivityStatus]
    TENANT_ACTIVITY_STATUS_UNFREEZING: _ClassVar[TenantActivityStatus]
    TENANT_ACTIVITY_STATUS_FREEZING: _ClassVar[TenantActivityStatus]
    TENANT_ACTIVITY_STATUS_ACTIVE: _ClassVar[TenantActivityStatus]
    TENANT_ACTIVITY_STATUS_INACTIVE: _ClassVar[TenantActivityStatus]
    TENANT_ACTIVITY_STATUS_OFFLOADED: _ClassVar[TenantActivityStatus]
    TENANT_ACTIVITY_STATUS_OFFLOADING: _ClassVar[TenantActivityStatus]
    TENANT_ACTIVITY_STATUS_ONLOADING: _ClassVar[TenantActivityStatus]

TENANT_ACTIVITY_STATUS_UNSPECIFIED: TenantActivityStatus
TENANT_ACTIVITY_STATUS_HOT: TenantActivityStatus
TENANT_ACTIVITY_STATUS_COLD: TenantActivityStatus
TENANT_ACTIVITY_STATUS_FROZEN: TenantActivityStatus
TENANT_ACTIVITY_STATUS_UNFREEZING: TenantActivityStatus
TENANT_ACTIVITY_STATUS_FREEZING: TenantActivityStatus
TENANT_ACTIVITY_STATUS_ACTIVE: TenantActivityStatus
TENANT_ACTIVITY_STATUS_INACTIVE: TenantActivityStatus
TENANT_ACTIVITY_STATUS_OFFLOADED: TenantActivityStatus
TENANT_ACTIVITY_STATUS_OFFLOADING: TenantActivityStatus
TENANT_ACTIVITY_STATUS_ONLOADING: TenantActivityStatus

class TenantsGetRequest(_message.Message):
    __slots__ = ("collection", "names")
    COLLECTION_FIELD_NUMBER: _ClassVar[int]
    NAMES_FIELD_NUMBER: _ClassVar[int]
    collection: str
    names: TenantNames
    def __init__(
        self,
        collection: _Optional[str] = ...,
        names: _Optional[_Union[TenantNames, _Mapping]] = ...,
    ) -> None: ...

class TenantNames(_message.Message):
    __slots__ = ("values",)
    VALUES_FIELD_NUMBER: _ClassVar[int]
    values: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, values: _Optional[_Iterable[str]] = ...) -> None: ...

class TenantsGetReply(_message.Message):
    __slots__ = ("took", "tenants")
    TOOK_FIELD_NUMBER: _ClassVar[int]
    TENANTS_FIELD_NUMBER: _ClassVar[int]
    took: float
    tenants: _containers.RepeatedCompositeFieldContainer[Tenant]
    def __init__(
        self,
        took: _Optional[float] = ...,
        tenants: _Optional[_Iterable[_Union[Tenant, _Mapping]]] = ...,
    ) -> None: ...

class Tenant(_message.Message):
    __slots__ = ("name", "activity_status")
    NAME_FIELD_NUMBER: _ClassVar[int]
    ACTIVITY_STATUS_FIELD_NUMBER: _ClassVar[int]
    name: str
    activity_status: TenantActivityStatus
    def __init__(
        self,
        name: _Optional[str] = ...,
        activity_status: _Optional[_Union[TenantActivityStatus, str]] = ...,
    ) -> None: ...
