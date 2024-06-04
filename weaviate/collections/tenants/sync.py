from weaviate import asyncify
from weaviate.collections.tenants.tenants import _TenantsAsync


@asyncify.convert
class _Tenants(_TenantsAsync):
    pass
