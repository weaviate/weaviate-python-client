from typing import Union
from weaviate.collections.classes.tenants import Tenant, TenantCreate, TenantUpdate

TenantCreateInputType = Union[str, Tenant, TenantCreate]
TenantUpdateInputType = Union[Tenant, TenantUpdate]
TenantOutputType = Tenant
