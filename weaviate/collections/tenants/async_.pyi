from typing import Dict, Optional, Sequence, Union

from weaviate.collections.classes.tenants import Tenant
from weaviate.collections.tenants.types import (
    TenantCreateInputType,
    TenantOutputType,
    TenantUpdateInputType,
)
from weaviate.connect.v4 import ConnectionAsync

from .executor import _TenantsExecutor

class _TenantsAsync(_TenantsExecutor[ConnectionAsync]):
    async def create(
        self, tenants: Union[TenantCreateInputType, Sequence[TenantCreateInputType]]
    ) -> None: ...
    async def remove(self, tenants: Union[str, Tenant, Sequence[Union[str, Tenant]]]) -> None: ...
    async def get(self) -> Dict[str, TenantOutputType]: ...
    async def get_by_names(
        self, tenants: Sequence[Union[str, Tenant]]
    ) -> Dict[str, TenantOutputType]: ...
    async def get_by_name(self, tenant: Union[str, Tenant]) -> Optional[TenantOutputType]: ...
    async def update(
        self, tenants: Union[TenantUpdateInputType, Sequence[TenantUpdateInputType]]
    ) -> None: ...
    async def exists(self, tenant: Union[str, Tenant]) -> bool: ...
