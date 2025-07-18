from typing import Union

from weaviate.collections.classes.tenants import Tenant, TenantCreate, TenantUpdate

TenantInputType = Union[str, Tenant]
TenantCreateInputType = Union[str, Tenant, TenantCreate]
TenantUpdateInputType = Union[Tenant, TenantUpdate]
TenantOutputType = Tenant
