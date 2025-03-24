from weaviate import syncify
from weaviate.connect.v4 import ConnectionSync
from weaviate.collections.tenants.async_ import _TenantsAsync, _TenantsBase


@syncify.convert_new(_TenantsAsync)
class _Tenants(_TenantsBase[ConnectionSync]):
    pass
