from weaviate.collections.classes.tenants import Tenant, TenantCreate, TenantUpdate

TenantInputType = str | Tenant
TenantCreateInputType = str | Tenant | TenantCreate
TenantUpdateInputType = Tenant | TenantUpdate
TenantOutputType = Tenant
