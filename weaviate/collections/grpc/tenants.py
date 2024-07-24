from typing import Optional, Sequence, cast

from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.tenants import TenantActivityStatus
from weaviate.collections.grpc.shared import _BaseGRPC
from weaviate.connect import ConnectionV4
from weaviate.proto.v1 import tenants_pb2


class _TenantsGRPC(_BaseGRPC):
    def __init__(
        self,
        connection: ConnectionV4,
        name: str,
        consistency_level: Optional[ConsistencyLevel],
    ):
        super().__init__(connection, consistency_level)
        self._name: str = name

    async def get(self, names: Optional[Sequence[str]]) -> tenants_pb2.TenantsGetReply:
        assert self._connection.grpc_stub is not None, "gRPC stub is not initialized"

        request = tenants_pb2.TenantsGetRequest(
            collection=self._name,
            names=tenants_pb2.TenantNames(values=names) if names is not None else None,
        )
        res = await self._connection.grpc_stub.TenantsGet(
            request,
            metadata=self._connection.grpc_headers(),
            timeout=self._connection.timeout_config.query,
        )
        return cast(tenants_pb2.TenantsGetReply, res)

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
