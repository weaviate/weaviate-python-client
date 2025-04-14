from typing import Dict, List, Literal, Union, overload
from weaviate.connect.v4 import ConnectionSync
from weaviate.users.executor import _DeprecatedExecutor, _DBExecutor, _OIDCExecutor
from weaviate.users.users import UserDB, OwnUser

from weaviate.rbac.models import Role, RoleBase
from typing_extensions import deprecated

class _UsersOIDC(_OIDCExecutor[ConnectionSync]):
    @overload
    def get_assigned_roles(
        self, *, user_id: str, include_permissions: Literal[False] = False
    ) -> Dict[str, RoleBase]: ...
    @overload
    def get_assigned_roles(
        self, *, user_id: str, include_permissions: Literal[True]
    ) -> Dict[str, Role]: ...
    @overload
    def get_assigned_roles(
        self, *, user_id: str, include_permissions: bool = False
    ) -> Union[Dict[str, Role], Dict[str, RoleBase]]: ...
    def assign_roles(self, *, user_id: str, role_names: Union[str, List[str]]) -> None: ...
    def revoke_roles(self, *, user_id: str, role_names: Union[str, List[str]]) -> None: ...

class _UsersDB(_DBExecutor[ConnectionSync]):
    @overload
    def get_assigned_roles(
        self, *, user_id: str, include_permissions: Literal[False] = False
    ) -> Dict[str, RoleBase]: ...
    @overload
    def get_assigned_roles(
        self, *, user_id: str, include_permissions: Literal[True]
    ) -> Dict[str, Role]: ...
    @overload
    def get_assigned_roles(
        self, *, user_id: str, include_permissions: bool = False
    ) -> Union[Dict[str, Role], Dict[str, RoleBase]]: ...
    def assign_roles(self, *, user_id: str, role_names: Union[str, List[str]]) -> None: ...
    def revoke_roles(self, *, user_id: str, role_names: Union[str, List[str]]) -> None: ...
    def create(self, *, user_id: str) -> str: ...
    def delete(self, *, user_id: str) -> bool: ...
    def rotate_key(self, *, user_id: str) -> str: ...
    def deactivate(self, *, user_id: str, revoke_key: bool = False) -> bool: ...
    def activate(self, *, user_id: str) -> bool: ...
    def get(self, *, user_id: str) -> UserDB: ...
    def list_all(self) -> List[UserDB]: ...

class _Users(_DeprecatedExecutor[ConnectionSync]):
    def get_my_user(self) -> OwnUser: ...
    @deprecated(
        """This method is deprecated and will be removed in Q4 25.
                Please use `users.db.get_assigned_roles` and/or `users.oidc.get_assigned_roles` instead."""
    )
    def get_assigned_roles(self, user_id: str) -> Dict[str, Role]: ...
    @deprecated(
        """This method is deprecated and will be removed in Q4 25.
                Please use `users.db.assign_roles` and/or `users.oidc.assign_roles` instead."""
    )
    def assign_roles(self, *, user_id: str, role_names: Union[str, List[str]]) -> None: ...
    @deprecated(
        """This method is deprecated and will be removed in Q4 25.
                Please use `users.db.revoke_roles` and/or `users.oidc.revoke_roles` instead."""
    )
    def revoke_roles(self, *, user_id: str, role_names: Union[str, List[str]]) -> None: ...
    db: _UsersDB
    oidc: _UsersOIDC
