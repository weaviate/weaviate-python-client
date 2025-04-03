from typing import Dict, List, Literal, Union, overload
from weaviate.connect.v4 import ConnectionAsync
from weaviate.users.executor import _DeprecatedExecutor, _DBExecutor, _OIDCExecutor
from weaviate.users.executor import UserDB, OwnUser

from weaviate.rbac.models import Role, RoleBase
from typing_extensions import deprecated

class _UsersOIDCAsync(_OIDCExecutor[ConnectionAsync]):
    @overload
    async def get_assigned_roles(
        self, *, user_id: str, include_permissions: Literal[False] = False
    ) -> Dict[str, RoleBase]: ...
    @overload
    async def get_assigned_roles(
        self, *, user_id: str, include_permissions: Literal[True]
    ) -> Dict[str, Role]: ...
    @overload
    async def get_assigned_roles(
        self, *, user_id: str, include_permissions: bool = False
    ) -> Union[Dict[str, Role], Dict[str, RoleBase]]: ...
    async def assign_roles(self, *, user_id: str, role_names: Union[str, List[str]]) -> None: ...
    async def revoke_roles(self, *, user_id: str, role_names: Union[str, List[str]]) -> None: ...

class _UsersDBAsync(_DBExecutor[ConnectionAsync]):
    @overload
    async def get_assigned_roles(
        self, *, user_id: str, include_permissions: Literal[False] = False
    ) -> Dict[str, RoleBase]: ...
    @overload
    async def get_assigned_roles(
        self, *, user_id: str, include_permissions: Literal[True]
    ) -> Dict[str, Role]: ...
    @overload
    async def get_assigned_roles(
        self, *, user_id: str, include_permissions: bool = False
    ) -> Union[Dict[str, Role], Dict[str, RoleBase]]: ...
    async def assign_roles(self, *, user_id: str, role_names: Union[str, List[str]]) -> None: ...
    async def revoke_roles(self, *, user_id: str, role_names: Union[str, List[str]]) -> None: ...
    async def create(self, *, user_id: str) -> str: ...
    async def delete(self, *, user_id: str) -> bool: ...
    async def rotate_key(self, *, user_id: str) -> str: ...
    async def deactivate(self, *, user_id: str, revoke_key: bool) -> bool: ...
    async def activate(self, *, user_id: str) -> bool: ...
    async def get(self, *, user_id: str) -> UserDB: ...
    async def list_all(self) -> List[UserDB]: ...

class _UsersAsync(_DeprecatedExecutor[ConnectionAsync]):
    async def get_my_user(self) -> OwnUser: ...
    @deprecated(
        """This method is deprecated and will be removed in Q4 25.
                Please use `users.db.get_assigned_roles` and/or `users.oidc.get_assigned_roles` instead."""
    )
    async def get_assigned_roles(self, user_id: str) -> Dict[str, Role]: ...
    @deprecated(
        """This method is deprecated and will be removed in Q4 25.
                Please use `users.db.assign_roles` and/or `users.oidc.assign_roles` instead."""
    )
    async def assign_roles(self, *, user_id: str, role_names: Union[str, List[str]]) -> None: ...
    @deprecated(
        """This method is deprecated and will be removed in Q4 25.
                Please use `users.db.revoke_roles` and/or `users.oidc.revoke_roles` instead."""
    )
    async def revoke_roles(self, *, user_id: str, role_names: Union[str, List[str]]) -> None: ...
    db: _UsersDBAsync
    oidc: _UsersOIDCAsync
