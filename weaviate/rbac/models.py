from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence, TypedDict, Union

from pydantic import BaseModel


class WeaviatePermission(TypedDict):
    action: str
    collection: str
    # object: Optional[str] not used yet, needs to be named different because of shadowing `object`
    role: str
    tenant: str


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
    action: CollectionsAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {"action": self.action, "collection": self.collection, "role": "*", "tenant": "*"}


class _DatabasePermission(_Permission):
    action: DatabaseAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {"action": self.action, "collection": "*", "role": "*", "tenant": "*"}


class _TenantPermission(_Permission):
    collection: str
    tenant: str
    action: TenantsAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
            "collection": self.collection,
            "tenant": self.tenant,
            "role": "*",
        }


@dataclass
class CollectionsPermission:
    collection: str
    action: CollectionsAction


@dataclass
class TenantsPermission:
    collection: str
    tenant: str
    action: TenantsAction


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
    ) -> Sequence[_CollectionsPermission]:
        """Create a permission specific to a collection to be used when creating and adding permissions to roles.

        Args:
            collection: The collection to grant permissions on.
            actions: The actions to grant on the collection.

        Returns:
            The collection permission.
        """
        if isinstance(actions, CollectionsAction):
            actions = [actions]

        return [_CollectionsPermission(collection=collection, action=action) for action in actions]

    @staticmethod
    def database(
        actions: Union[DatabaseAction, List[DatabaseAction]]
    ) -> Sequence[_DatabasePermission]:
        """Create a database permission to be used when creating and adding permissions to roles.

        Args:
            actions: The actions to grant on the database.

        Returns:
            The database permission.
        """
        if isinstance(actions, DatabaseAction):
            actions = [actions]

        return [_DatabasePermission(action=action) for action in actions]

    @staticmethod
    def tenant(
        collection: str, tenant: str, actions: Union[TenantsAction, List[TenantsAction]]
    ) -> Sequence[_TenantPermission]:
        """Create a tenant permission to be used when creating and adding permissions to roles.

        Args:
            collection: The collection to grant permissions on.
            tenant: The tenant to grant permissions on.1
            actions: The actions to grant on the tenant.

        Returns:
            The tenant permission.
        """
        if isinstance(actions, TenantsAction):
            actions = [actions]

        return [
            _TenantPermission(collection=collection, tenant=tenant, action=action)
            for action in actions
        ]


class RBAC:
    actions = ActionsFactory
    permissions = PermissionsFactory
