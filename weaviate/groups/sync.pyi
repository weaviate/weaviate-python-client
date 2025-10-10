from typing import Literal, overload

from weaviate.connect.v4 import ConnectionSync
from weaviate.groups.base import _GroupsOIDCExecutor
from weaviate.rbac.models import Role, RoleBase

class _GroupsOIDC(_GroupsOIDCExecutor[ConnectionSync]):
    @overload
    def get_assigned_roles(
        self, *, group_id: str, include_permissions: Literal[False] = False
    ) -> dict[str, RoleBase]: ...
    @overload
    def get_assigned_roles(
        self, *, group_id: str, include_permissions: Literal[True]
    ) -> dict[str, Role]: ...
    @overload
    def get_assigned_roles(
        self, *, group_id: str, include_permissions: bool = False
    ) -> dict[str, Role] | dict[str, RoleBase]: ...
    def assign_roles(self, *, group_id: str, role_names: str | list[str]) -> None: ...
    def revoke_roles(self, *, group_id: str, role_names: str | list[str]) -> None: ...
    def get_known_group_names(self) -> list[str]: ...

class _Groups:
    def __init__(self, connection: ConnectionSync): ...
    @property
    def oidc(self) -> _GroupsOIDC: ...
