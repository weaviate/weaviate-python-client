from typing import Dict, Optional, Sequence, Union

from weaviate.collections.classes.tenants import Tenant
from weaviate.collections.tenants.types import (
    TenantCreateInputType,
    TenantOutputType,
    TenantUpdateInputType,
)
from weaviate.connect.v4 import ConnectionSync

from .executor import _TenantsExecutor

class _Tenants(_TenantsExecutor[ConnectionSync]):
    def create(
        self, tenants: Union[TenantCreateInputType, Sequence[TenantCreateInputType]]
    ) -> None: ...
    def remove(self, tenants: Union[str, Tenant, Sequence[Union[str, Tenant]]]) -> None: ...
    def get(self) -> Dict[str, TenantOutputType]: ...
    def get_by_names(
        self, tenants: Sequence[Union[str, Tenant]]
    ) -> Dict[str, TenantOutputType]: ...
    def get_by_name(self, tenant: Union[str, Tenant]) -> Optional[TenantOutputType]: ...
    def update(
        self, tenants: Union[TenantUpdateInputType, Sequence[TenantUpdateInputType]]
    ) -> None: ...
    def exists(self, tenant: Union[str, Tenant]) -> bool: ...
