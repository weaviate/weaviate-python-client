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
    user: str
    tenant: str


class WeaviateRole(TypedDict):
    name: str
    permissions: List[WeaviatePermission]


class _Action:
    pass


class TenantsAction(str, _Action, Enum):
    CREATE = "create_meta_tenants"
    READ = "read_meta_tenants"
    UPDATE = "update_meta_tenants"
    DELETE = "delete_meta_tenants"

    @staticmethod
    def values() -> List[str]:
        return [action.value for action in TenantsAction]


class CollectionsAction(str, _Action, Enum):
    CREATE = "create_meta_collections"
    READ = "read_meta_collections"
    UPDATE = "update_meta_collections"
    DELETE = "delete_meta_collections"

    @staticmethod
    def values() -> List[str]:
        return [action.value for action in CollectionsAction]


class ObjectsCollectionAction(str, _Action, Enum):
    CREATE = "create_data_collection_objects"
    READ = "read_data_collection_objects"
    UPDATE = "update_data_collection_objects"
    DELETE = "delete_data_collection_objects"

    @staticmethod
    def values() -> List[str]:
        return [action.value for action in ObjectsCollectionAction]


class ObjectsTenantAction(str, _Action, Enum):
    CREATE = "create_data_tenant_objects"
    READ = "read_data_tenant_objects"
    UPDATE = "update_data_tenant_objects"
    DELETE = "delete_data_tenant_objects"

    @staticmethod
    def values() -> List[str]:
        return [action.value for action in ObjectsTenantAction]


class RolesAction(str, _Action, Enum):
    MANAGE = "manage_roles"
    READ = "read_roles"

    @staticmethod
    def values() -> List[str]:
        return [action.value for action in RolesAction]


class UsersAction(str, _Action, Enum):
    MANAGE = "manage_users"

    @staticmethod
    def values() -> List[str]:
        return [action.value for action in UsersAction]


class ClusterAction(str, _Action, Enum):
    MANAGE_CLUSTER = "manage_cluster"

    @staticmethod
    def values() -> List[str]:
        return [action.value for action in ClusterAction]


class _Permission(BaseModel):
    @abstractmethod
    def _to_weaviate(self) -> WeaviatePermission:
        raise NotImplementedError()


class _CollectionsPermission(_Permission):
    collection: str
    action: CollectionsAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
            "collection": self.collection,
            "role": "*",
            "tenant": "*",
            "user": "*",
        }


class _RolesPermission(_Permission):
    role: str
    action: RolesAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
            "collection": "*",
            "role": self.role,
            "tenant": "*",
            "user": "*",
        }


class _UsersPermission(_Permission):
    user: str
    action: UsersAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
            "user": self.user,
            "role": "*",
            "tenant": "*",
            "collection": "*",
        }


class _ClusterPermission(_Permission):
    action: ClusterAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
            "role": "*",
            "tenant": "*",
            "user": "*",
            "collection": "*",
        }


class _TenantsPermission(_Permission):
    collection: str
    tenant: str
    action: TenantsAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
            "collection": self.collection,
            "tenant": self.tenant,
            "role": "*",
            "user": "*",
        }


class _ObjectsCollectionPermission(_Permission):
    collection: str
    action: ObjectsCollectionAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
            "collection": self.collection,
            "role": "*",
            "tenant": "*",
            "user": "*",
        }


class _ObjectsTenantPermission(_Permission):
    collection: str
    tenant: str
    action: ObjectsTenantAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
            "collection": self.collection,
            "tenant": self.tenant,
            "role": "*",
            "user": "*",
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
class RolesPermission:
    role: str
    action: RolesAction


@dataclass
class Role:
    name: str
    cluster_actions: Optional[List[ClusterAction]]
    users_actions: Optional[List[UsersAction]]
    collections_permissions: Optional[List[CollectionsPermission]]
    tenants_permissions: Optional[List[TenantsPermission]]
    roles_permissions: Optional[List[RolesPermission]]


@dataclass
class User:
    name: str


Actions = Union[_Action, Sequence[_Action]]
Permissions = Union[_Permission, Sequence[_Permission]]


class _ObjectsCollectionFactory:
    @staticmethod
    def create(collection: str) -> _ObjectsCollectionPermission:
        return _ObjectsCollectionPermission(
            collection=collection, action=ObjectsCollectionAction.CREATE
        )

    @staticmethod
    def read(collection: str) -> _ObjectsCollectionPermission:
        return _ObjectsCollectionPermission(
            collection=collection, action=ObjectsCollectionAction.READ
        )

    @staticmethod
    def update(collection: str) -> _ObjectsCollectionPermission:
        return _ObjectsCollectionPermission(
            collection=collection, action=ObjectsCollectionAction.UPDATE
        )

    @staticmethod
    def delete(collection: str) -> _ObjectsCollectionPermission:
        return _ObjectsCollectionPermission(
            collection=collection, action=ObjectsCollectionAction.DELETE
        )


class _ObjectsTenantFactory:
    @staticmethod
    def create(collection: str, tenant: str) -> _ObjectsTenantPermission:
        return _ObjectsTenantPermission(
            collection=collection, tenant=tenant, action=ObjectsTenantAction.CREATE
        )

    @staticmethod
    def read(collection: str, tenant: str) -> _ObjectsTenantPermission:
        return _ObjectsTenantPermission(
            collection=collection, tenant=tenant, action=ObjectsTenantAction.READ
        )

    @staticmethod
    def update(collection: str, tenant: str) -> _ObjectsTenantPermission:
        return _ObjectsTenantPermission(
            collection=collection, tenant=tenant, action=ObjectsTenantAction.UPDATE
        )

    @staticmethod
    def delete(collection: str, tenant: str) -> _ObjectsTenantPermission:
        return _ObjectsTenantPermission(
            collection=collection, tenant=tenant, action=ObjectsTenantAction.DELETE
        )


class _CollectionsFactory:
    objects = _ObjectsCollectionFactory

    @staticmethod
    def create(collection: Optional[str] = None) -> _CollectionsPermission:
        return _CollectionsPermission(collection=collection or "*", action=CollectionsAction.CREATE)

    @staticmethod
    def read(collection: Optional[str] = None) -> _CollectionsPermission:
        return _CollectionsPermission(collection=collection or "*", action=CollectionsAction.READ)

    @staticmethod
    def update(collection: Optional[str] = None) -> _CollectionsPermission:
        return _CollectionsPermission(collection=collection or "*", action=CollectionsAction.UPDATE)

    @staticmethod
    def delete(collection: Optional[str] = None) -> _CollectionsPermission:
        return _CollectionsPermission(collection=collection or "*", action=CollectionsAction.DELETE)


class _TenantsFactory:
    objects = _ObjectsTenantFactory

    @staticmethod
    def create(collection: str, tenant: Optional[str] = None) -> _TenantsPermission:
        return _TenantsPermission(
            collection=collection, tenant=tenant or "*", action=TenantsAction.CREATE
        )

    @staticmethod
    def read(collection: str, tenant: Optional[str] = None) -> _TenantsPermission:
        return _TenantsPermission(
            collection=collection, tenant=tenant or "*", action=TenantsAction.READ
        )

    @staticmethod
    def update(collection: str, tenant: Optional[str] = None) -> _TenantsPermission:
        return _TenantsPermission(
            collection=collection, tenant=tenant or "*", action=TenantsAction.UPDATE
        )

    @staticmethod
    def delete(collection: str, tenant: Optional[str] = None) -> _TenantsPermission:
        return _TenantsPermission(
            collection=collection, tenant=tenant or "*", action=TenantsAction.DELETE
        )


class _RolesFactory:
    @staticmethod
    def manage(role: Optional[str] = None) -> _RolesPermission:
        return _RolesPermission(role=role or "*", action=RolesAction.MANAGE)

    @staticmethod
    def read(role: Optional[str] = None) -> _RolesPermission:
        return _RolesPermission(role=role or "*", action=RolesAction.READ)


class _UsersFactory:
    @staticmethod
    def manage(user: Optional[str] = None) -> _UsersPermission:
        return _UsersPermission(user=user or "*", action=UsersAction.MANAGE)


class _ClusterFactory:
    @staticmethod
    def manage() -> _ClusterPermission:
        return _ClusterPermission(action=ClusterAction.MANAGE_CLUSTER)


class ActionsFactory:
    cluster = ClusterAction
    collection = CollectionsAction
    roles = RolesAction
    users = UsersAction
    tenants = TenantsAction


class PermissionsFactory:
    cluser = _ClusterFactory
    collections = _CollectionsFactory
    roles = _RolesFactory
    tenants = _TenantsFactory


class RBAC:
    actions = ActionsFactory
    permissions = PermissionsFactory
