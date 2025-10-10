from typing import Literal, overload

from weaviate.connect.v4 import ConnectionAsync
from weaviate.groups.base import _GroupsOIDCExecutor
from weaviate.rbac.models import Role, RoleBase

class _GroupsOIDCAsync(_GroupsOIDCExecutor[ConnectionAsync]):
    @overload
    async def get_assigned_roles(
        self, *, group_id: str, include_permissions: Literal[False] = False
    ) -> dict[str, RoleBase]: ...
    @overload
    async def get_assigned_roles(
        self, *, group_id: str, include_permissions: Literal[True]
    ) -> dict[str, Role]: ...
    @overload
    async def get_assigned_roles(
        self, *, group_id: str, include_permissions: bool = False
    ) -> dict[str, Role] | dict[str, RoleBase]: ...
    async def assign_roles(self, *, group_id: str, role_names: str | list[str]) -> None: ...
    async def revoke_roles(self, *, group_id: str, role_names: str | list[str]) -> None: ...
    async def get_known_group_names(self) -> list[str]: ...

class _GroupsAsync:
    def __init__(self, connection: ConnectionAsync): ...
    @property
    def oidc(self) -> _GroupsOIDCAsync: ...
