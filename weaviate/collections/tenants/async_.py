from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync
from weaviate.collections.tenants.executor import _TenantsExecutor


@executor.wrap("async")
class _TenantsAsync(_TenantsExecutor[ConnectionAsync]):
    pass
