from typing import Optional, Sequence

from weaviate.collections.classes.tenants import TenantActivityStatus
from weaviate.collections.grpc.shared import _BaseGRPC
from weaviate.proto.v1 import tenants_pb2
from weaviate.util import _ServerVersion


class _TenantsGRPC(_BaseGRPC):
    def __init__(
        self,
        weaviate_version: _ServerVersion,
        name: str,
    ):
        super().__init__(weaviate_version, None, False)
        self._name: str = name

    def get(self, names: Optional[Sequence[str]]) -> tenants_pb2.TenantsGetRequest:
        return tenants_pb2.TenantsGetRequest(
            collection=self._name,
            names=tenants_pb2.TenantNames(values=names) if names is not None else None,
        )

    def map_activity_status(self, status: tenants_pb2.TenantActivityStatus) -> TenantActivityStatus:
        if (
            status == tenants_pb2.TENANT_ACTIVITY_STATUS_COLD
            or status == tenants_pb2.TENANT_ACTIVITY_STATUS_INACTIVE
        ):
            return TenantActivityStatus.INACTIVE
        if (
            status == tenants_pb2.TENANT_ACTIVITY_STATUS_HOT
            or status == tenants_pb2.TENANT_ACTIVITY_STATUS_ACTIVE
        ):
            return TenantActivityStatus.ACTIVE
        if (
            status == tenants_pb2.TENANT_ACTIVITY_STATUS_FROZEN
            or status == tenants_pb2.TENANT_ACTIVITY_STATUS_OFFLOADED
        ):
            return TenantActivityStatus.OFFLOADED
        if (
            status == tenants_pb2.TENANT_ACTIVITY_STATUS_FREEZING
            or status == tenants_pb2.TENANT_ACTIVITY_STATUS_OFFLOADING
        ):
            return TenantActivityStatus.OFFLOADING
        if (
            status == tenants_pb2.TENANT_ACTIVITY_STATUS_UNFREEZING
            or status == tenants_pb2.TENANT_ACTIVITY_STATUS_ONLOADING
        ):
            return TenantActivityStatus.ONLOADING
        raise ValueError(f"Unknown TenantActivityStatus: {status}")
