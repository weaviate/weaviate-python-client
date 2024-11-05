from typing import List, Union

from weaviate.connect import ConnectionV4
from weaviate.rbac.models import (
    CollectionAction,
    DatabaseAction,
    _CollectionPermission,
    _DatabasePermission,
    Permissions,
)


class _Permissions:
    def __init__(self, connection: ConnectionV4) -> None:
        self._connection = connection

    def add(self, *, permissions: Permissions, role: str) -> None:
        """Add permissions to a role.

        Args:
            permissions: The permissions to add to the role.
            role: The role to add the permissions to.
        """
        ...

    def remove(self, *, permissions: Permissions, role: str) -> None:
        """Remove permissions from a role.

        Args:
            actions: The actions to remove from the role.
            role: The role to remove the permissions from.
        """
        ...


class ActionsFactory:
    collection = CollectionAction
    database = DatabaseAction


class PermissionsFactory:
    @staticmethod
    def collection(
        collection: str, actions: Union[CollectionAction, List[CollectionAction]]
    ) -> _CollectionPermission:
        """Create a permission specific to a collection to be used when creating and adding permissions to roles.

        Args:
            collection: The collection to grant permissions on.
            actions: The actions to grant on the collection.

        Returns:
            The collection permission.
        """
        return _CollectionPermission(
            resource=collection,
            actions=[actions] if isinstance(actions, CollectionAction) else actions,
        )

    @staticmethod
    def database(actions: Union[DatabaseAction, List[DatabaseAction]]) -> _DatabasePermission:
        """Create a database permission to be used when creating and adding permissions to roles.

        Args:
            actions: The actions to grant on the database.

        Returns:
            The database permission.
        """
        return _DatabasePermission(
            actions=[actions] if isinstance(actions, DatabaseAction) else actions
        )


class RBAC:
    actions = ActionsFactory
    permissions = PermissionsFactory
