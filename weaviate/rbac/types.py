from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Literal, Optional, Sequence, TypedDict, Union

from pydantic import BaseModel


class WeaviatePermission(TypedDict):
    actions: List[str]
    level: Literal["collection", "database"]
    resources: List[str]


class WeaviateRole(TypedDict):
    name: str
    permissions: List[WeaviatePermission]


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


class _Permission(BaseModel):
    @abstractmethod
    def _to_weaviate(self) -> WeaviatePermission:
        raise NotImplementedError()


class _CollectionPermission(_Permission):
    resource: str
    actions: List[CollectionAction]

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "actions": [action.value for action in self.actions],
            "level": "collection",
            "resources": [self.resource],
        }


class _DatabasePermission(_Permission):
    actions: List[DatabaseAction]

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "actions": [action.value for action in self.actions],
            "level": "database",
            "resources": [],
        }


@dataclass
class CollectionPermission:
    resource: str
    actions: List[CollectionAction]


@dataclass
class DatabasePermission:
    actions: List[DatabaseAction]


@dataclass
class Role:
    name: str
    collection_permissions: Optional[List[CollectionPermission]]
    database_permissions: Optional[List[DatabasePermission]]


@dataclass
class User:
    name: str


Actions = Union[_Action, Sequence[_Action]]
Permissions = Union[_Permission, Sequence[_Permission]]


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
