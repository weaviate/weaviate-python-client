from dataclasses import dataclass
from typing import List, Optional, Union

from weaviate.connect import ConnectionV4
from weaviate.rbac.permissions import (
    _Permissions,
    CollectionPermission,
    DatabasePermission,
    Permissions,
)


@dataclass
class Role:
    name: str
    collection_permissions: Optional[List[CollectionPermission]]
    database_permissions: Optional[List[DatabasePermission]]


class _Roles:
    def __init__(self, connection: ConnectionV4) -> None:
        self.permissions = _Permissions(connection)

    def list_all(self) -> List[Role]:  # type: ignore
        """Get all roles.

        Returns:
            All roles.
        """
        ...

    def by_name(self, role: str) -> Optional[Role]:
        """Get the permissions granted to this role.

        Args:
            role: The name of the role to get the permissions for.

        Returns:
            A `Role` object or `None` if it does not exist.
        """
        ...

    def by_user(self, user: str) -> List[Role]:  # type: ignore
        """Get the roles assigned to a user.

        Args:
            user: The user ID to get the roles for.

        Returns:
            A list of `Role` objects.
        """
        ...

    def users(self, role: str) -> List[str]:  # type: ignore
        """Get the users that have been assigned this role.

        Args:
            role: The role to get the users for.

        Returns:
            A list of user IDs.
        """
        ...

    def delete(self, role: str) -> None:
        """Delete a role.

        Args:
            role: The name of the role to delete.
        """
        ...

    def create(self, *, name: str, permissions: Permissions) -> Role:  # type: ignore
        """Create a new role.

        Args:
            name: The name of the role.
            permissions: The permissions of the role.

        Returns:
            The created role.
        """
        ...

    def assign(self, *, roles: Union[str, List[str]], user: str) -> None:
        """Assign roles to a user.

        Args:
            roles: The roles to assign to the user.
            user: The user to assign the roles to.
        """
        ...

    def revoke(self, *, roles: Union[str, List[str]], user: str) -> None:
        """Remove roles from a user.

        Args:
            roles: The roles to remove from the user.
            user: The user to remove the roles from.
        """
        ...
