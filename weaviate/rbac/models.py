from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence, TypedDict, Union

from pydantic import BaseModel


class WeaviatePermission(TypedDict):
    actions: List[str]
    resources: List[str]


class WeaviateRole(TypedDict):
    name: str
    permissions: List[WeaviatePermission]


class _Action:
    pass


class TenantsAction(str, _Action, Enum):
    CREATE_OBJECTS = "create_objects_tenant"
    READ_OBJECTS = "read_objects_tenant"
    UPDATE_OBJECTS = "update_objects_tenant"
    DELETE_OBJECTS = "delete_objects_tenant"

    @staticmethod
    def values() -> List[str]:
        return [action.value for action in TenantsAction]


class CollectionsAction(str, _Action, Enum):
    CREATE_OBJECTS = "create_objects_collection"
    READ_OBJECTS = "read_objects_collection"
    UPDATE_OBJECTS = "update_objects_collection"
    DELETE_OBJECTS = "delete_objects_collection"

    CREATE_TENANTS = "create_tenants"
    READ_TENANTS = "read_tenants"
    UPDATE_TENANTS = "update_tenants"
    DELETE_TENANTS = "delete_tenants"

    @staticmethod
    def values() -> List[str]:
        return [action.value for action in CollectionsAction]


class DatabaseAction(str, _Action, Enum):
    CREATE_COLLECTIONS = "create_collections"
    READ_COLLECTIONS = "read_collections"
    UPDATE_COLLECTIONS = "update_collections"
    DELETE_COLLECTIONS = "delete_collections"

    MANAGE_CLUSTER = "manage_cluster"
    MANAGE_ROLES = "manage_roles"
    READ_ROLES = "read_roles"

    @staticmethod
    def values() -> List[str]:
        return [action.value for action in DatabaseAction]


class _Permission(BaseModel):
    @abstractmethod
    def _to_weaviate(self) -> WeaviatePermission:
        raise NotImplementedError()


class _CollectionsPermission(_Permission):
    collection: str
    actions: List[CollectionsAction]

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "actions": [action.value for action in self.actions],
            "resources": [self.collection],
        }


class _DatabasePermission(_Permission):
    actions: List[DatabaseAction]

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "actions": [action.value for action in self.actions],
            "resources": [],
        }


class _TenantPermission(_Permission):
    collection: str
    tenant: str
    actions: List[TenantsAction]

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "actions": [action.value for action in self.actions],
            "resources": [f"{self.collection};;{self.tenant}"],
        }


@dataclass
class CollectionsPermission:
    collection: str
    actions: List[CollectionsAction]


@dataclass
class TenantsPermission:
    collection: str
    tenant: str
    actions: List[TenantsAction]


@dataclass
class Role:
    name: str
    collections_permissions: Optional[List[CollectionsPermission]]
    database_permissions: Optional[List[DatabaseAction]]
    tenants_permissions: Optional[List[TenantsPermission]]


@dataclass
class User:
    name: str


Actions = Union[_Action, Sequence[_Action]]
Permissions = Union[_Permission, Sequence[_Permission]]


class ActionsFactory:
    collection = CollectionsAction
    database = DatabaseAction


class PermissionsFactory:
    @staticmethod
    def collection(
        collection: str, actions: Union[CollectionsAction, List[CollectionsAction]]
    ) -> _CollectionsPermission:
        """Create a permission specific to a collection to be used when creating and adding permissions to roles.

        Args:
            collection: The collection to grant permissions on.
            actions: The actions to grant on the collection.

        Returns:
            The collection permission.
        """
        return _CollectionsPermission(
            collection=collection,
            actions=[actions] if isinstance(actions, CollectionsAction) else actions,
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
        collection: str, tenant: str, actions: Union[TenantsAction, List[TenantsAction]]
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
            actions=[actions] if isinstance(actions, TenantsAction) else actions,
        )


class RBAC:
    actions = ActionsFactory
    permissions = PermissionsFactory
