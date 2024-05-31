from weaviate import asyncify
from weaviate.collections.tenants.async_ import _TenantsAsync


@asyncify.convert
class _Tenants(_TenantsAsync):
    pass
