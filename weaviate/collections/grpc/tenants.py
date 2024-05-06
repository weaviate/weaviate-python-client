from typing import Optional, Sequence

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

    def get(self, names: Optional[Sequence[str]]) -> tenants_pb2.TenantsGetReply:
        assert self._connection.grpc_stub is not None, "gRPC stub is not initialized"

        request = tenants_pb2.TenantsGetRequest(
            collection=self._name,
            names=tenants_pb2.TenantNames(values=names) if names is not None else None,
        )
        res: tenants_pb2.TenantsGetReply  # According to PEP-0526
        res, _ = self._connection.grpc_stub.TenantsGet.with_call(
            request,
            metadata=self._connection.grpc_headers(),
            timeout=self._connection.timeout_config.query,
        )
        return res

    def map_activity_status(self, status: tenants_pb2.TenantActivityStatus) -> TenantActivityStatus:
        if status == tenants_pb2.TENANT_ACTIVITY_STATUS_COLD:
            return TenantActivityStatus.COLD
        if status == tenants_pb2.TENANT_ACTIVITY_STATUS_HOT:
            return TenantActivityStatus.HOT
        if status == tenants_pb2.TENANT_ACTIVITY_STATUS_FROZEN:
            return TenantActivityStatus.FROZEN
        if status == tenants_pb2.TENANT_ACTIVITY_STATUS_WARM:
            return TenantActivityStatus.WARM
        raise ValueError(f"Unknown TenantActivityStatus: {status}")
