from dataclasses import dataclass
from enum import Enum
from typing import List, Sequence, Union

from weaviate.connect import ConnectionV4


class _Permission:
    pass


class _Action:
    pass


class CollectionAction(str, _Action, Enum):
    CREATE_TENANT = "create_tenant"
    READ_TENANT = "read_tenant"
    UPDATE_TENANT = "update_tenant"
    DELETE_TENANT = "delete_tenant"

    CREATE_OBJECT = "create_object"
    READ_OBJECT = "read_object"
    UPDATE_OBJECT = "update_object"
    DELETE_OBJECT = "delete_object"


class DatabaseAction(str, _Action, Enum):
    CREATE_COLLECTION = "create_collection"
    READ_COLLECTION = "read_collection"
    UPDATE_COLLECTION = "update_collection"
    DELETE_COLLECTION = "delete_collection"

    CREATE_ROLE = "create_role"
    READ_ROLE = "read_role"
    UPDATE_ROLE = "update_role"
    DELETE_ROLE = "delete_role"


@dataclass
class CollectionPermission(_Permission):
    collection: str
    actions: List[CollectionAction]


@dataclass
class DatabasePermission(_Permission):
    actions: List[DatabaseAction]


Actions = Union[_Action, Sequence[_Action]]
Permissions = Union[_Permission, Sequence[_Permission]]


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
    def collection(  # type: ignore
        collection: str, actions: Union[CollectionAction, List[CollectionAction]]
    ) -> CollectionPermission:
        """Create a permission specific to a collection.

        Args:
            collection: The collection to grant permissions on.
            actions: The actions to grant on the collection.

        Returns:
            The collection permission.
        """
        ...

    @staticmethod
    def database(actions: Union[DatabaseAction, List[DatabaseAction]]) -> DatabasePermission:  # type: ignore
        """Create a database permission.

        Args:
            actions: The actions to grant on the database.

        Returns:
            The database permission.
        """
        ...


class RBAC:
    actions = ActionsFactory
    permissions = PermissionsFactory
