from weaviate.connect import impl
from weaviate.connect.v4 import ConnectionAsync
from weaviate.collections.tenants.base import _TenantsBase


@impl.generate("async")
class _TenantsAsync(_TenantsBase[ConnectionAsync]):
    pass
