from typing import Dict, List, Optional, Sequence, Union

from weaviate.rbac.models import (
    PermissionsOutputType,
    PermissionsInputType,
    Role,
)
from weaviate.rbac.roles import _RolesBase

class _Roles(_RolesBase):
    def list_all(self) -> Dict[str, Role]: ...
    def get(self, role_name: str) -> Optional[Role]: ...
    def get_assigned_user_ids(self, role_name: str) -> List[str]: ...
    def get_assigned_db_user_ids(self, role_name: str) -> List[str]: ...
    def get_assigned_oidc_user_ids(self, role_name: str) -> List[str]: ...
    def delete(self, role_name: str) -> None: ...
    def create(self, *, role_name: str, permissions: PermissionsInputType) -> Role: ...
    def exists(self, *, role_name: str) -> bool: ...
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
