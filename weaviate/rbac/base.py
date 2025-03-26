from abc import abstractmethod
from typing import Dict, Generic, List, Optional, Sequence, Union

from weaviate.connect.executor import ExecutorResult
from weaviate.connect.v4 import ConnectionType
from weaviate.rbac.executor import _RolesExecutor
from weaviate.rbac.models import PermissionsOutputType, PermissionsInputType, Role, UserAssignment


class _RolesBase(Generic[ConnectionType]):
    _executor = _RolesExecutor()

    def __init__(self, connection: ConnectionType) -> None:
        self._connection: ConnectionType = connection

    @abstractmethod
    def list_all(self) -> ExecutorResult[Dict[str, Role]]:
        """Get all roles.

        Returns:
            A dictionary with user names as keys and the `Role` objects as values.
        """
        raise NotImplementedError()

    @abstractmethod
    def exists(self, role_name: str) -> ExecutorResult[bool]:
        """Check if a role exists.

        Args:
            role_name: The name of the role to check.

        Returns:
            True if the role exists, False otherwise.
        """
        raise NotImplementedError()

    @abstractmethod
    def get(self, role_name: str) -> ExecutorResult[Optional[Role]]:
        """Get the permissions granted to this role.

        Args:
            role_name: The name of the role to get the permissions for.

        Returns:
            A `Role` object or `None` if it does not exist.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_assigned_db_user_ids(self, role_name: str) -> ExecutorResult[List[str]]:
        """Get the ids of DB users that have been assigned this role.

        Args:
            role_name: The role to get the users for.

        Returns:
            A list of ids.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_assigned_oidc_user_ids(self, role_name: str) -> ExecutorResult[List[str]]:
        """Get the ids of OIDC users that have been assigned this role.

        Args:
            role_name: The role to get the users for.

        Returns:
            A list of ids.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_assigned_user_ids(self, role_name: str) -> ExecutorResult[List[str]]:
        """Get the ids of user that have been assigned this role.

        Args:
            role_name: The role to get the users for.

        Returns:
            A list of ids.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_user_assignments(self, role_name: str) -> ExecutorResult[List[UserAssignment]]:
        """Get the ids and usertype of users that have been assigned this role.

        Args:
            role_name: The role to get the users for.

        Returns:
            A list of Assignments.
        """
        raise NotImplementedError()

    @abstractmethod
    def delete(self, role_name: str) -> ExecutorResult[None]:
        """Delete a role.

        Args:
            role_name: The name of the role to delete.
        """
        raise NotImplementedError()

    @abstractmethod
    def create(self, *, role_name: str, permissions: PermissionsInputType) -> ExecutorResult[Role]:
        """Create a new role.

        Args:
            role_name: The name of the role.
            permissions: The permissions of the role.

        Returns:
            The created role.
        """
        raise NotImplementedError()

    @abstractmethod
    def add_permissions(
        self, *, permissions: PermissionsInputType, role_name: str
    ) -> ExecutorResult[None]:
        """Add permissions to a role.

        Note: This method is an upsert operation. If the permission already exists, it will be updated. If it does not exist, it will be created.

        Args:
            permissions: The permissions to add to the role.
            role_name: The name of the role to add the permissions to.
        """
        raise NotImplementedError()

    @abstractmethod
    def remove_permissions(
        self, *, permissions: PermissionsInputType, role_name: str
    ) -> ExecutorResult[None]:
        """Remove permissions from a role.

        Note: This method is a downsert operation. If the permission does not exist, it will be ignored. If these permissions are the only permissions of the role, the role will be deleted.

        Args:
            permissions: The permissions to remove from the role.
            role_name: The name of the role to remove the permissions from.
        """
        raise NotImplementedError()

    @abstractmethod
    def has_permissions(
        self,
        *,
        permissions: Union[
            PermissionsInputType, PermissionsOutputType, Sequence[PermissionsOutputType]
        ],
        role: str,
    ) -> ExecutorResult[bool]:
        """Check if a role has a specific set of permission.

        Args:
            permission: The permission to check.
            role: The role to check the permission for.

        Returns:
            True if the role has the permission, False otherwise.
        """
        raise NotImplementedError()
