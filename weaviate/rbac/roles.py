import json
from typing import Dict, List, Optional, Union, cast

from weaviate.connect import ConnectionV4
from weaviate.connect.v4 import _ExpectedStatusCodes
from weaviate.rbac.models import (
    _Permission,
    PermissionsOutputType,
    PermissionsInputType,
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

    async def _get_current_roles(self) -> List[WeaviateRole]:
        path = "/authz/users/own-roles"

        res = await self._connection.get(
            path,
            error_msg="Could not get roles",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get own roles"),
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
        path = f"/authz/roles/{role}/add-permissions"

        await self._connection.post(
            path,
            weaviate_object={"permissions": permissions},
            error_msg="Could not add permissions",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Add permissions"),
        )

    async def _remove_permissions(self, permissions: List[WeaviatePermission], role: str) -> None:
        path = f"/authz/roles/{role}/remove-permissions"

        await self._connection.post(
            path,
            weaviate_object={"permissions": permissions},
            error_msg="Could not remove permissions",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Remove permissions"),
        )

    async def _has_permission(self, permission: WeaviatePermission, role: str) -> bool:
        path = f"/authz/roles/{role}/has-permission"

        res = await self._connection.post(
            path,
            weaviate_object=permission,
            error_msg="Could not check permission",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Check permission"),
        )
        return cast(bool, res.json())


class _RolesAsync(_RolesBase):
    def __user_from_weaviate_user(self, user: str) -> User:
        return User(name=user)

    async def list_all(self) -> Dict[str, Role]:
        """Get all roles.

        Returns:
            A dictionary with user names as keys and the `Role` objects as values.
        """
        return {role["name"]: Role._from_weaviate_role(role) for role in await self._get_roles()}

    async def of_current_user(self) -> Dict[str, Role]:
        """Get all roles for current user. The user is determined by the API key supplied to the client.

        Returns:
            A dictionary with user names as keys and the `Role` objects as values.
        """
        return {
            role["name"]: Role._from_weaviate_role(role) for role in await self._get_current_roles()
        }

    async def exists(self, role_name: str) -> bool:
        """Check if a role exists.

        Args:
            role_name: The name of the role to check.

        Returns:
            True if the role exists, False otherwise.
        """
        return await self._get_role(role_name) is not None

    async def by_name(self, role_name: str) -> Optional[Role]:
        """Get the permissions granted to this role.

        Args:
            role_name: The name of the role to get the permissions for.

        Returns:
            A `Role` object or `None` if it does not exist.
        """
        r = await self._get_role(role_name)
        if r is None:
            return None
        return Role._from_weaviate_role(r)

    async def by_user(self, user: str) -> Dict[str, Role]:
        """Get the roles assigned to a user.

        Args:
            user: The user ID to get the roles for.

        Returns:
            A dictionary with user names as keys and the `Role` objects as values.
        """
        return {
            role["name"]: Role._from_weaviate_role(role)
            for role in await self._get_roles_of_user(user)
        }

    async def assigned_users(self, role_name: str) -> Dict[str, User]:
        """Get the users that have been assigned this role.

        Args:
            role_name: The role to get the users for.

        Returns:
            A dictionary with user names as keys and the `User` objects as values.
        """
        return {
            user: self.__user_from_weaviate_user(user)
            for user in await self._get_users_of_role(role_name)
        }

    async def delete(self, role_name: str) -> None:
        """Delete a role.

        Args:
            role_name: The name of the role to delete.
        """
        return await self._delete_role(role_name)

    async def create(self, *, role_name: str, permissions: PermissionsInputType) -> Role:
        """Create a new role.

        Args:
            role_name: The name of the role.
            permissions: The permissions of the role.

        Returns:
            The created role.
        """
        role: WeaviateRole = {
            "name": role_name,
            "permissions": [
                permission._to_weaviate() for permission in _flatten_permissions(permissions)
            ],
        }
        return Role._from_weaviate_role(await self._post_roles(role))

    async def assign_to_user(self, *, role_names: Union[str, List[str]], user: str) -> None:
        """Assign roles to a user.

        Args:
            role_names: The names of the roles to assign to the user.
            user: The user to assign the roles to.
        """
        await self._assign_roles_to_user(
            [role_names] if isinstance(role_names, str) else role_names, user
        )

    async def revoke_from_user(self, *, role_names: Union[str, List[str]], user: str) -> None:
        """Revoke roles from a user.

        Args:
            role_names: The names of the roles to revoke from the user.
            user: The user to revoke the roles from.
        """
        await self._revoke_roles_from_user(
            [role_names] if isinstance(role_names, str) else role_names, user
        )

    async def add_permissions(self, *, permissions: PermissionsInputType, role_name: str) -> None:
        """Add permissions to a role.

        Note: This method is an upsert operation. If the permission already exists, it will be updated. If it does not exist, it will be created.

        Args:
            permissions: The permissions to add to the role.
            role_name: The name of the role to add the permissions to.
        """
        if isinstance(permissions, _Permission):
            permissions = [permissions]
        await self._add_permissions(
            [permission._to_weaviate() for permission in _flatten_permissions(permissions)],
            role_name,
        )

    async def remove_permissions(
        self, *, permissions: PermissionsInputType, role_name: str
    ) -> None:
        """Remove permissions from a role.

        Note: This method is a downsert operation. If the permission does not exist, it will be ignored. If these permissions are the only permissions of the role, the role will be deleted.

        Args:
            permissions: The permissions to remove from the role.
            role_name: The name of the role to remove the permissions from.
        """
        if isinstance(permissions, _Permission):
            permissions = [permissions]
        await self._remove_permissions(
            [permission._to_weaviate() for permission in _flatten_permissions(permissions)],
            role_name,
        )

    async def has_permission(
        self, *, permission: Union[_Permission, PermissionsOutputType], role: str
    ) -> bool:
        """Check if a role has a specific permission.

        Args:
            permission: The permission to check.
            role: The role to check the permission for.

        Returns:
            True if the role has the permission, False otherwise.
        """
        return await self._has_permission(permission._to_weaviate(), role)


def _flatten_permissions(permissions: PermissionsInputType) -> List[_Permission]:
    if isinstance(permissions, _Permission):
        return [permissions]
    flattened_permissions: List[_Permission] = []
    for permission in permissions:
        if isinstance(permission, _Permission):
            flattened_permissions.append(permission)
        else:
            flattened_permissions.extend(permission)
    return flattened_permissions
