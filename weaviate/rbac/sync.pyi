import asyncio
import json
from typing import Dict, Generic, List, Optional, Sequence, Union, cast
from typing_extensions import deprecated
from httpx import Response
from weaviate.connect.v4 import _ExpectedStatusCodes, ConnectionType, ConnectionAsync
from weaviate.connect import executor
from weaviate.rbac.models import (
    _Permission,
    PermissionsOutputType,
    PermissionsInputType,
    Role,
    UserAssignment,
    UserTypes,
    WeaviatePermission,
    WeaviateRole,
)
from weaviate.connect.v4 import ConnectionSync
from .executor import _RolesExecutor

class _Roles(_RolesExecutor[ConnectionSync]):
    def list_all(self) -> Dict[str, Role]: ...
    def get_current_roles(self) -> List[Role]: ...
    def exists(self, role_name: str) -> bool: ...
    def get(self, role_name: str) -> Optional[Role]: ...
    def create(self, *, role_name: str, permissions: PermissionsInputType) -> Role: ...
    def get_user_assignments(self, role_name: str) -> List[UserAssignment]: ...
    @deprecated(
        "This method is deprecated and will be removed in Q4 25. Please use `roles.get_user_assignments` instead."
    )
    def get_assigned_user_ids(self, role_name: str) -> List[str]: ...
    def delete(self, role_name: str) -> None: ...
    def add_permissions(self, *, permissions: PermissionsInputType, role_name: str) -> None: ...
    def remove_permissions(self, *, permissions: PermissionsInputType, role_name: str) -> None: ...
    def has_permissions(
        self,
        *,
        permissions: Union[
            PermissionsInputType, PermissionsOutputType, Sequence[PermissionsOutputType]
        ],
        role: str
    ) -> bool: ...
