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


def _flatten_permissions(
    permissions: Union[PermissionsInputType, PermissionsOutputType, Sequence[PermissionsOutputType]]
) -> List[_Permission]:
    if isinstance(permissions, _Permission):
        return [permissions]
    flattened_permissions: List[_Permission] = []
    for permission in permissions:
        if isinstance(permission, _Permission):
            flattened_permissions.append(permission)
        else:
            flattened_permissions.extend(permission)
    return flattened_permissions


class _RolesExecutor(Generic[ConnectionType]):
    def __init__(self, connection: ConnectionType):
        self._connection = connection

    def list_all(self) -> executor.Result[Dict[str, Role]]:
        """Get all roles.

        Returns:
            A dictionary with user names as keys and the `Role` objects as values.
        """
        path = "/authz/roles"

        def resp(res: Response) -> Dict[str, Role]:
            return {role["name"]: Role._from_weaviate_role(role) for role in res.json()}

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path=path,
            error_msg="Could not get roles",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get roles"),
        )

    def get_current_roles(self) -> executor.Result[List[Role]]:
        # TODO: Add documentation here and this method to the stubs plus tests
        path = "/authz/users/own-roles"

        def resp(res: Response) -> List[Role]:
            return [Role._from_weaviate_role(role) for role in cast(List[WeaviateRole], res.json())]

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path=path,
            error_msg="Could not get roles",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get own roles"),
        )

    def exists(self, role_name: str) -> executor.Result[bool]:
        """Check if a role exists.

        Args:
            role_name: The name of the role to check.

        Returns:
            True if the role exists, False otherwise.
        """
        path = f"/authz/roles/{role_name}"

        def resp(res: Response) -> bool:
            return res.status_code == 200

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path=path,
            error_msg=f"Could not get role {role_name}",
            status_codes=_ExpectedStatusCodes(ok_in=[200, 404], error="Get role"),
        )

    def get(self, role_name: str) -> executor.Result[Optional[Role]]:
        """Get the permissions granted to this role.

        Args:
            role_name: The name of the role to get the permissions for.

        Returns:
            A `Role` object or `None` if it does not exist.
        """
        path = f"/authz/roles/{role_name}"

        def resp(res: Response) -> Optional[Role]:
            if res.status_code == 404:
                return None
            return Role._from_weaviate_role(cast(WeaviateRole, res.json()))

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path=path,
            error_msg=f"Could not get role {role_name}",
            status_codes=_ExpectedStatusCodes(ok_in=[200, 404], error="Get role"),
        )

    def create(self, *, role_name: str, permissions: PermissionsInputType) -> executor.Result[Role]:
        """Create a new role.

        Args:
            role_name: The name of the role.
            permissions: The permissions of the role.

        Returns:
            The created role.
        """
        path = "/authz/roles"

        perms = []
        for perm in _flatten_permissions(permissions):
            perms.extend(perm._to_weaviate())

        role: WeaviateRole = {
            "name": role_name,
            "permissions": perms,
        }

        def resp(res: Response) -> Role:
            return Role._from_weaviate_role(role)

        return executor.execute(
            response_callback=resp,
            method=self._connection.post,
            path=path,
            weaviate_object=role,
            error_msg=f"Could not create role: {json.dumps(role)}",
            status_codes=_ExpectedStatusCodes(ok_in=[201], error="Create role"),
        )

    def get_user_assignments(self, role_name: str) -> executor.Result[List[UserAssignment]]:
        """Get the ids and usertype of users that have been assigned this role.

        Args:
            role_name: The role to get the users for.

        Returns:
            A list of Assignments.
        """
        path = f"/authz/roles/{role_name}/user-assignments"

        def resp(res: Response) -> List[UserAssignment]:
            return [
                UserAssignment(
                    user_id=assignment["userId"], user_type=UserTypes(assignment["userType"])
                )
                for assignment in res.json()
            ]

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path=path,
            error_msg=f"Could not get users of role {role_name}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get users of role"),
        )

    @deprecated(
        """This method is deprecated and will be removed in Q4 25. Please use `roles.get_user_assignments` instead."""
    )
    def get_assigned_user_ids(
        self,
        role_name: str,
    ) -> executor.Result[List[str]]:
        """Get the ids of user that have been assigned this role.

        Args:
            role_name: The role to get the users for.

        Returns:
            A list of ids.
        """
        path = f"/authz/roles/{role_name}/users"

        def resp(res: Response) -> List[str]:
            return cast(List[str], res.json())

        return executor.execute(
            response_callback=resp,
            method=self._connection.get,
            path=path,
            error_msg=f"Could not get users of role {role_name}",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Get users of role"),
        )

    def delete(
        self,
        role_name: str,
    ) -> executor.Result[None]:
        """Delete a role.

        Args:
            role_name: The name of the role to delete.
        """
        path = f"/authz/roles/{role_name}"

        def resp(res: Response) -> None:
            return None

        return executor.execute(
            response_callback=resp,
            method=self._connection.delete,
            path=path,
            error_msg=f"Could not delete role {role_name}",
            status_codes=_ExpectedStatusCodes(ok_in=[204], error="Delete role"),
        )

    def add_permissions(
        self, *, permissions: PermissionsInputType, role_name: str
    ) -> executor.Result[None]:
        """Add permissions to a role.

        Note: This method is an upsert operation. If the permission already exists, it will be updated. If it does not exist, it will be created.

        Args:
            permissions: The permissions to add to the role.
            role_name: The name of the role to add the permissions to.
        """
        path = f"/authz/roles/{role_name}/add-permissions"

        if isinstance(permissions, _Permission):
            permissions = [permissions]

        def resp(res: Response) -> None:
            return None

        return executor.execute(
            response_callback=resp,
            method=self._connection.post,
            path=path,
            weaviate_object={
                "permissions": [
                    weav_perm
                    for perm in _flatten_permissions(permissions)
                    for weav_perm in perm._to_weaviate()
                ]
            },
            error_msg="Could not add permissions",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Add permissions"),
        )

    def remove_permissions(
        self, *, permissions: PermissionsInputType, role_name: str
    ) -> executor.Result[None]:
        """Remove permissions from a role.

        Note: This method is a downsert operation. If the permission does not exist, it will be ignored. If these permissions are the only permissions of the role, the role will be deleted.

        Args:
            permissions: The permissions to remove from the role.
            role_name: The name of the role to remove the permissions from.
        """
        path = f"/authz/roles/{role_name}/remove-permissions"

        if isinstance(permissions, _Permission):
            permissions = [permissions]

        def resp(res: Response) -> None:
            return None

        return executor.execute(
            response_callback=resp,
            method=self._connection.post,
            path=path,
            weaviate_object={
                "permissions": [
                    weav_perm
                    for perm in _flatten_permissions(permissions)
                    for weav_perm in perm._to_weaviate()
                ]
            },
            error_msg="Could not remove permissions",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="Remove permissions"),
        )

    def __has_permission(
        self,
        *,
        permission: WeaviatePermission,
        role: str,
    ) -> executor.Result[bool]:
        path = f"/authz/roles/{role}/has-permission"

        def resp(res: Response) -> bool:
            return res.status_code == 200

        return executor.execute(
            response_callback=resp,
            method=self._connection.post,
            path=path,
            weaviate_object=permission,
            error_msg="Could not check permission",
            status_codes=_ExpectedStatusCodes(ok_in=[200, 404], error="Check permission"),
        )

    def has_permissions(
        self,
        *,
        permissions: Union[
            PermissionsInputType, PermissionsOutputType, Sequence[PermissionsOutputType]
        ],
        role: str,
    ) -> executor.Result[bool]:
        """Check if a role has a specific set of permission.

        Args:
            permission: The permission to check.
            role: The role to check the permission for.

        Returns:
            True if the role has the permission, False otherwise.
        """
        if isinstance(self._connection, ConnectionAsync):

            async def execute() -> bool:
                return all(
                    await asyncio.gather(
                        *[
                            executor.aresult(self.__has_permission(permission=weav_perm, role=role))
                            for permission in _flatten_permissions(permissions)
                            for weav_perm in permission._to_weaviate()
                        ]
                    )
                )

            return execute()

        return all(
            executor.result(self.__has_permission(permission=weav_perm, role=role))
            for permission in _flatten_permissions(permissions)
            for weav_perm in permission._to_weaviate()
        )
