from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync
from weaviate.collections.tenants.base import _TenantsBase


@executor.wrap("sync")
class _Tenants(_TenantsBase[ConnectionSync]):
    pass
