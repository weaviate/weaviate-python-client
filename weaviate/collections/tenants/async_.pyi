import asyncio
from math import ceil
from typing import Any, Dict, Generic, List, Optional, Sequence, Union
from httpx import Response
from weaviate.collections.classes.tenants import (
    Tenant,
    TenantCreate,
    TenantUpdate,
    TenantActivityStatus,
    TenantCreateActivityStatus,
    TenantUpdateActivityStatus,
    TenantOutput,
)
from weaviate.collections.grpc.tenants import _TenantsGRPC
from weaviate.collections.tenants.types import (
    TenantCreateInputType,
    TenantUpdateInputType,
    TenantOutputType,
)
from weaviate.connect import executor
from weaviate.connect.v4 import _ExpectedStatusCodes, ConnectionAsync, ConnectionType
from weaviate.exceptions import WeaviateInvalidInputError
from weaviate.proto.v1 import tenants_pb2
from weaviate.validator import _validate_input, _ValidateArgument
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
