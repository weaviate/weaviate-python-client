from typing import Dict, List, Optional, Sequence, Union

from typing_extensions import deprecated

from weaviate.connect.v4 import ConnectionSync
from weaviate.rbac.models import (
    GroupAssignment,
    PermissionsInputType,
    PermissionsOutputType,
    Role,
    UserAssignment,
)

from .executor import _RolesExecutor

class _Roles(_RolesExecutor[ConnectionSync]):
    def list_all(self) -> Dict[str, Role]: ...
    @deprecated(
        "This method is deprecated and will be removed in Q4 25. Please use `users.get_my_user()` instead."
    )
    def get_current_roles(self) -> List[Role]: ...
    def exists(self, role_name: str) -> bool: ...
    def get(self, role_name: str) -> Optional[Role]: ...
    def create(self, *, role_name: str, permissions: PermissionsInputType) -> Role: ...
    def get_user_assignments(self, role_name: str) -> List[UserAssignment]: ...
    def get_group_assignments(self, role_name: str) -> List[GroupAssignment]: ...
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
        role: str,
    ) -> bool: ...
