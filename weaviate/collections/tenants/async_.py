from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync
from weaviate.collections.tenants.base import _TenantsBase


@executor.wrap("async")
class _TenantsAsync(_TenantsBase[ConnectionAsync]):
    pass
