from weaviate.collections.tenants.executor import _TenantsExecutor
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync


@executor.wrap("sync")
class _Tenants(_TenantsExecutor[ConnectionSync]):
    pass
