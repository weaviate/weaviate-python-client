from typing import Dict, Generic, List, Optional, Sequence, Union
from typing_extensions import deprecated

from weaviate.connect.executor import aresult
from weaviate.connect.v4 import ConnectionAsync, ConnectionType
from weaviate.rbac.executor import _RolesExecutor
from weaviate.rbac.models import (
    PermissionsOutputType,
    PermissionsInputType,
    Role,
)


class _RolesBase(Generic[ConnectionType]):
    _executor = _RolesExecutor()

    def __init__(self, connection: ConnectionType) -> None:
        self._connection: ConnectionType = connection


class _RolesAsync(_RolesBase[ConnectionAsync]):
    async def list_all(self) -> Dict[str, Role]:
        """Get all roles.

        Returns:
            A dictionary with user names as keys and the `Role` objects as values.
        """
        return await aresult(self._executor.list_all(self._connection))

    async def exists(self, role_name: str) -> bool:
        """Check if a role exists.

        Args:
            role_name: The name of the role to check.

        Returns:
            True if the role exists, False otherwise.
        """
        return await aresult(self._executor.exists(role_name, connection=self._connection))

    async def get(self, role_name: str) -> Optional[Role]:
        """Get the permissions granted to this role.

        Args:
            role_name: The name of the role to get the permissions for.

        Returns:
            A `Role` object or `None` if it does not exist.
        """
        return await aresult(self._executor.get(role_name, connection=self._connection))

    async def get_assigned_db_user_ids(self, role_name: str) -> List[str]:
        """Get the ids of DB users that have been assigned this role.

        Args:
            role_name: The role to get the users for.

        Returns:
            A list of ids.
        """
        return await aresult(
            self._executor.get_assigned_db_user_ids(role_name, connection=self._connection)
        )

    async def get_assigned_oidc_user_ids(self, role_name: str) -> List[str]:
        """Get the ids of OIDC users that have been assigned this role.

        Args:
            role_name: The role to get the users for.

        Returns:
            A list of ids.
        """
        return await aresult(
            self._executor.get_assigned_oidc_user_ids(role_name, connection=self._connection)
        )

    @deprecated(
        """This method is deprecated and will be removed in Q4 25.
                Please use `roles.get_assigned_db_user_ids` and/or `roles.get_assigned_oidc_user_ids` instead."""
    )
    async def get_assigned_user_ids(self, role_name: str) -> List[str]:
        """Get the ids of user that have been assigned this role.

        Args:
            role_name: The role to get the users for.

        Returns:
            A list of ids.
        """
        return await aresult(
            self._executor.get_assigned_user_ids(role_name, connection=self._connection)
        )

    async def delete(self, role_name: str) -> None:
        """Delete a role.

        Args:
            role_name: The name of the role to delete.
        """
        return await aresult(self._executor.delete(role_name, connection=self._connection))

    async def create(self, *, role_name: str, permissions: PermissionsInputType) -> Role:
        """Create a new role.

        Args:
            role_name: The name of the role.
            permissions: The permissions of the role.

        Returns:
            The created role.
        """
        return await aresult(
            self._executor.create(
                connection=self._connection, permissions=permissions, role_name=role_name
            )
        )

    async def add_permissions(self, *, permissions: PermissionsInputType, role_name: str) -> None:
        """Add permissions to a role.

        Note: This method is an upsert operation. If the permission already exists, it will be updated. If it does not exist, it will be created.

        Args:
            permissions: The permissions to add to the role.
            role_name: The name of the role to add the permissions to.
        """
        return await aresult(
            self._executor.add_permissions(
                self._connection, permissions=permissions, role_name=role_name
            )
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
        return await aresult(
            self._executor.remove_permissions(
                self._connection, permissions=permissions, role_name=role_name
            )
        )

    async def has_permissions(
        self,
        *,
        permissions: Union[
            PermissionsInputType, PermissionsOutputType, Sequence[PermissionsOutputType]
        ],
        role: str,
    ) -> bool:
        """Check if a role has a specific set of permission.

        Args:
            permission: The permission to check.
            role: The role to check the permission for.

        Returns:
            True if the role has the permission, False otherwise.
        """
        return await aresult(
            self._executor.has_permissions(
                connection=self._connection, permissions=permissions, role=role
            )
        )
