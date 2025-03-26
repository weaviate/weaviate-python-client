from weaviate.connect import impl
from weaviate.connect.v4 import ConnectionSync
from weaviate.collections.tenants.base import _TenantsBase


@impl.generate("sync")
class _Tenants(_TenantsBase[ConnectionSync]):
    pass
