import json
from typing import List, Optional, Union, cast

from weaviate.connect import ConnectionV4
from weaviate.connect.v4 import _ExpectedStatusCodes
from weaviate.rbac.models import (
    Permissions,
    _Permission,
    Role,
    User,
    WeaviatePermission,
    WeaviateRole,
)


class _RolesBase:
    def __init__(self, connection: ConnectionV4) -> None:
        self._connection = connection

    async def _get_roles(self) -> List[WeaviateRole]:
        path = "/authz/roles"

        res = await self._connection.get(
            path,
            error_msg="Could not get roles",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get roles"),
        )
        return cast(List[WeaviateRole], res.json())

    async def _get_role(self, name: str) -> Optional[WeaviateRole]:
        path = f"/authz/roles/{name}"

        res = await self._connection.get(
            path,
            error_msg=f"Could not get role {name}",
            status_codes=_ExpectedStatusCodes(ok_in=[200, 404], error="Get role"),
        )
        if res.status_code == 404:
            return None
        return cast(Optional[WeaviateRole], res.json())

    async def _post_roles(self, role: WeaviateRole) -> WeaviateRole:
        path = "/authz/roles"

        await self._connection.post(
            path,
            weaviate_object=role,
            error_msg=f"Could not create role: {json.dumps(role)}",
            status_codes=_ExpectedStatusCodes(ok_in=[201], error="Create role"),
        )
        return role

    async def _delete_role(self, name: str) -> None:
        path = f"/authz/roles/{name}"

        await self._connection.delete(
            path,
            error_msg=f"Could not delete role {name}",
            status_codes=_ExpectedStatusCodes(ok_in=[204], error="Delete role"),
        )

    async def _get_users_of_role(self, name: str) -> List[str]:
        path = f"/authz/roles/{name}/users"

        res = await self._connection.get(
            path,
            error_msg=f"Could not get users of role {name}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get users of role"),
        )
        return cast(List[str], res.json())

    async def _get_roles_of_user(self, name: str) -> List[WeaviateRole]:
        path = f"/authz/users/{name}/roles"

        res = await self._connection.get(
            path,
            error_msg=f"Could not get roles of user {name}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get roles of user"),
        )
        return cast(List[WeaviateRole], res.json())

    async def _assign_roles_to_user(self, roles: List[str], user: str) -> None:
        path = f"/authz/users/{user}/assign"

        await self._connection.post(
            path,
            weaviate_object={"roles": roles},
            error_msg=f"Could not assign roles {roles} to user {user}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Assign user to roles"),
        )

    async def _revoke_roles_from_user(self, roles: List[str], user: str) -> None:
        path = f"/authz/users/{user}/revoke"

        await self._connection.post(
            path,
            weaviate_object={"roles": roles},
            error_msg=f"Could not revoke roles {roles} from user {user}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Revoke roles from user"),
        )

    async def _add_permissions(self, permissions: List[WeaviatePermission], role: str) -> None:
        path = "/authz/roles/add-permissions"

        await self._connection.post(
            path,
            weaviate_object={"permissions": permissions, "name": role},
            error_msg="Could not add permissions",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Add permissions"),
        )

    async def _remove_permissions(self, permissions: List[WeaviatePermission], role: str) -> None:
        path = "/authz/roles/remove-permissions"

        await self._connection.post(
            path,
            weaviate_object={"permissions": permissions, "name": role},
            error_msg="Could not remove permissions",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Remove permissions"),
        )


class _RolesAsync(_RolesBase):
    def __user_from_weaviate_user(self, user: str) -> User:
        return User(name=user)

    async def list_all(self) -> List[Role]:
        """Get all roles.

        Returns:
            All roles.
        """
        return [Role._from_weaviate_role(role) for role in await self._get_roles()]

    async def exists(self, role: str) -> bool:
        """Check if a role exists.

        Args:
            role: The name of the role to check.

        Returns:
            True if the role exists, False otherwise.
        """
        return await self._get_role(role) is not None

    async def by_name(self, role: str) -> Optional[Role]:
        """Get the permissions granted to this role.

        Args:
            role: The name of the role to get the permissions for.

        Returns:
            A `Role` object or `None` if it does not exist.
        """
        r = await self._get_role(role)
        if r is None:
            return None
        return Role._from_weaviate_role(r)

    async def by_user(self, user: str) -> List[Role]:
        """Get the roles assigned to a user.

        Args:
            user: The user ID to get the roles for.

        Returns:
            A list of `Role` objects.
        """
        return [Role._from_weaviate_role(role) for role in await self._get_roles_of_user(user)]

    async def users(self, role: str) -> List[User]:
        """Get the users that have been assigned this role.

        Args:
            role: The role to get the users for.

        Returns:
            A list of user IDs.
        """
        return [
            self.__user_from_weaviate_user(user) for user in await self._get_users_of_role(role)
        ]

    async def delete(self, role: str) -> None:
        """Delete a role.

        Args:
            role: The name of the role to delete.
        """
        return await self._delete_role(role)

    async def create(self, *, name: str, permissions: Permissions) -> Role:
        """Create a new role.

        Args:
            name: The name of the role.
            permissions: The permissions of the role.

        Returns:
            The created role.
        """
        if isinstance(permissions, _Permission):
            permissions = [permissions]
        role: WeaviateRole = {
            "name": name,
            "permissions": [permission._to_weaviate() for permission in permissions],
        }
        return Role._from_weaviate_role(await self._post_roles(role))

    async def assign(self, *, roles: Union[str, List[str]], user: str) -> None:
        """Assign roles to a user.

        Args:
            roles: The roles to assign to the user.
            user: The user to assign the roles to.
        """
        await self._assign_roles_to_user([roles] if isinstance(roles, str) else roles, user)

    async def revoke(self, *, roles: Union[str, List[str]], user: str) -> None:
        """Revoke roles from a user.

        Args:
            roles: The roles to revoke from the user.
            user: The user to revoke the roles from.
        """
        await self._revoke_roles_from_user([roles] if isinstance(roles, str) else roles, user)

    async def add_permissions(self, *, permissions: Permissions, role: str) -> None:
        """Add permissions to a role.

        Note: This method is an upsert operation. If the permission already exists, it will be updated. If it does not exist, it will be created.

        Args:
            permissions: The permissions to add to the role.
            role: The role to add the permissions to.
        """
        if isinstance(permissions, _Permission):
            permissions = [permissions]
        await self._add_permissions([permission._to_weaviate() for permission in permissions], role)

    async def remove_permissions(self, *, permissions: Permissions, role: str) -> None:
        """Remove permissions from a role.

        Note: This method is a downsert operation. If the permission does not exist, it will be ignored. If these permissions are the only permissions of the role, the role will be deleted.

        Args:
            permissions: The permissions to remove from the role.
            role: The role to remove the permissions from.
        """
        if isinstance(permissions, _Permission):
            permissions = [permissions]
        await self._remove_permissions(
            [permission._to_weaviate() for permission in permissions], role
        )
