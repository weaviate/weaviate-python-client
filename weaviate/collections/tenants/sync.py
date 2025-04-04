from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync
from weaviate.collections.tenants.executor import _TenantsExecutor


@executor.wrap("sync")
class _Tenants(_TenantsExecutor[ConnectionSync]):
    pass
