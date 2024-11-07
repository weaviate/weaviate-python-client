from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Literal, Optional, Sequence, TypedDict, Union

from pydantic import BaseModel


class WeaviatePermission(TypedDict):
    actions: List[str]
    level: Literal["collection", "database", "tenant"]
    resources: List[str]


class WeaviateRole(TypedDict):
    name: str
    permissions: List[WeaviatePermission]


class _Action:
    pass


class TenantActions(str, _Action, Enum):
    CREATE_OBJECTS = "create_objects"
    READ_OBJECTS = "read_objects"
    UPDATE_OBJECTS = "update_objects"
    DELETE_OBJECTS = "delete_objects"


class CollectionActions(str, _Action, Enum):
    CREATE_TENANTS = "create_tenants"
    READ_TENANTS = "read_tenants"
    UPDATE_TENANTS = "update_tenants"
    DELETE_TENANTS = "delete_tenants"

    CREATE_OBJECTS = "create_objects"
    READ_OBJECTS = "read_objects"
    UPDATE_OBJECTS = "update_objects"
    DELETE_OBJECTS = "delete_objects"


class DatabaseAction(str, _Action, Enum):
    CREATE_COLLECTION = "create_collections"
    READ_COLLECTION = "read_collections"
    UPDATE_COLLECTION = "update_collections"
    DELETE_COLLECTION = "delete_collections"

    MANAGE_CLUSTER = "manage_cluster"
    MANAGE_ROLES = "manage_roles"
    READ_ROLES = "read_roles"


class _Permission(BaseModel):
    @abstractmethod
    def _to_weaviate(self) -> WeaviatePermission:
        raise NotImplementedError()


class _CollectionPermission(_Permission):
    collection: str
    actions: List[CollectionActions]

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "actions": [action.value for action in self.actions],
            "level": "collection",
            "resources": [self.collection],
        }


class _DatabasePermission(_Permission):
    actions: List[DatabaseAction]

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "actions": [action.value for action in self.actions],
            "level": "database",
            "resources": [],
        }


class _TenantPermission(_Permission):
    collection: str
    tenant: str
    actions: List[TenantActions]

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "actions": [action.value for action in self.actions],
            "level": "tenant",
            "resources": [f"{self.collection}/{self.tenant}"],
        }


@dataclass
class CollectionPermission:
    collection: str
    actions: List[CollectionActions]


@dataclass
class DatabasePermission:
    actions: List[DatabaseAction]


@dataclass
class TenantPermission:
    collection: str
    tenant: str
    actions: List[TenantActions]


@dataclass
class Role:
    name: str
    collection_permissions: Optional[List[CollectionPermission]]
    database_permissions: Optional[List[DatabasePermission]]
    tenant_permissions: Optional[List[TenantPermission]]


@dataclass
class User:
    name: str


Actions = Union[_Action, Sequence[_Action]]
Permissions = Union[_Permission, Sequence[_Permission]]


class ActionsFactory:
    collection = CollectionActions
    database = DatabaseAction


class PermissionsFactory:
    @staticmethod
    def collection(
        collection: str, actions: Union[CollectionActions, List[CollectionActions]]
    ) -> _CollectionPermission:
        """Create a permission specific to a collection to be used when creating and adding permissions to roles.

        Args:
            collection: The collection to grant permissions on.
            actions: The actions to grant on the collection.

        Returns:
            The collection permission.
        """
        return _CollectionPermission(
            collection=collection,
            actions=[actions] if isinstance(actions, CollectionActions) else actions,
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

    @staticmethod
    def tenant(
        collection: str, tenant: str, actions: Union[TenantActions, List[TenantActions]]
    ) -> _TenantPermission:
        """Create a tenant permission to be used when creating and adding permissions to roles.

        Args:
            collection: The collection to grant permissions on.
            tenant: The tenant to grant permissions on.1
            actions: The actions to grant on the tenant.

        Returns:
            The tenant permission.
        """
        return _TenantPermission(
            collection=collection,
            tenant=tenant,
            actions=[actions] if isinstance(actions, TenantActions) else actions,
        )


class RBAC:
    actions = ActionsFactory
    permissions = PermissionsFactory
