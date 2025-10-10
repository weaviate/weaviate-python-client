from typing import Optional, Sequence

from typing_extensions import deprecated

from weaviate.connect.v4 import ConnectionAsync
from weaviate.rbac.models import (
    GroupAssignment,
    PermissionsInputType,
    PermissionsOutputType,
    Role,
    UserAssignment,
)

from .executor import _RolesExecutor

class _RolesAsync(_RolesExecutor[ConnectionAsync]):
    async def list_all(self) -> dict[str, Role]: ...
    @deprecated(
        "This method is deprecated and will be removed in Q4 25. Please use `users.get_my_user()` instead."
    )
    async def get_current_roles(self) -> list[Role]: ...
    async def exists(self, role_name: str) -> bool: ...
    async def get(self, role_name: str) -> Optional[Role]: ...
    async def create(self, *, role_name: str, permissions: PermissionsInputType) -> Role: ...
    async def get_user_assignments(self, role_name: str) -> list[UserAssignment]: ...
    async def get_group_assignments(self, role_name: str) -> list[GroupAssignment]: ...
    @deprecated(
        "This method is deprecated and will be removed in Q4 25. Please use `roles.get_user_assignments` instead."
    )
    async def get_assigned_user_ids(self, role_name: str) -> list[str]: ...
    async def delete(self, role_name: str) -> None: ...
    async def add_permissions(
        self, *, permissions: PermissionsInputType, role_name: str
    ) -> None: ...
    async def remove_permissions(
        self, *, permissions: PermissionsInputType, role_name: str
    ) -> None: ...
    async def has_permissions(
        self,
        *,
        permissions: PermissionsInputType | PermissionsOutputType | Sequence[PermissionsOutputType],
        role: str,
    ) -> bool: ...
