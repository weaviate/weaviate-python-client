from weaviate import syncify
from weaviate.collections.tenants.tenants import _TenantsAsync


@syncify.convert
class _Tenants(_TenantsAsync):
    pass
