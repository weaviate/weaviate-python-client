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


class RolesAction(str, _Action, Enum):
    MANAGE = "manage_roles"
    READ = "read_roles"

    @staticmethod
    def values() -> List[str]:
        return [action.value for action in RolesAction]


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
        return {"action": self.action, "collection": self.collection, "role": "*", "tenant": "*"}


class _RolesPermission(_Permission):
    role: str
    action: RolesAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {"action": self.action, "collection": "*", "role": self.role, "tenant": "*"}


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
    collections_permissions: Optional[List[CollectionsPermission]]
    tenants_permissions: Optional[List[TenantsPermission]]
    roles_permissions: Optional[List[RolesPermission]]


@dataclass
class User:
    name: str


Actions = Union[_Action, Sequence[_Action]]
Permissions = Union[_Permission, Sequence[_Permission]]


class ActionsFactory:
    cluster = ClusterAction
    collection = CollectionsAction
    roles = RolesAction
    tenants = TenantsAction


class PermissionsFactory:
    @staticmethod
    def collections(
        *,
        collection: Optional[str] = None,
        actions: Union[CollectionsAction, List[CollectionsAction]]
    ) -> List[_CollectionsPermission]:
        """Create a permission specific to a collection to be used when creating and adding permissions to roles.

        Granting this permission will implicitly grant all permissions on all tenants and objects in the collection.
        For finer-grained control, use the `tenants` permission.

        Args:
            collection: The collection to grant permissions on. If not provided, the permission will be granted on all collections.
            actions: The actions to grant on the collection permission.

        Returns:
            The collection permission.
        """
        if isinstance(actions, CollectionsAction):
            actions = [actions]

        return [
            _CollectionsPermission(collection=collection or "*", action=action)
            for action in actions
        ]

    @staticmethod
    def roles(
        *, role: Optional[str] = None, actions: Union[RolesAction, List[RolesAction]]
    ) -> List[_RolesPermission]:
        """Create a roles permission to be used when creating and adding permissions to roles.

        Args:
            role: The role to grant permissions on. If not provided, the permission will be granted on all roles.
            actions: The actions to grant on the roles permission.

        Returns:
            The role permission.
        """
        if isinstance(actions, RolesAction):
            actions = [actions]

        return [_RolesPermission(action=action, role=role or "*") for action in actions]

    @staticmethod
    def tenants(
        *,
        collection: str,
        tenant: Optional[str] = None,
        actions: Union[TenantsAction, List[TenantsAction]]
    ) -> List[_TenantsPermission]:
        """Create a tenant permission to be used when creating and adding permissions to roles.

        Args:
            collection: The collection to grant permissions on.
            tenant: The tenant to grant permissions on. If not provided, the permission will be granted on all tenants in this collection.
            actions: The actions to grant on the tenant.

        Returns:
            The tenant permission.
        """
        if isinstance(actions, TenantsAction):
            actions = [actions]

        return [
            _TenantsPermission(collection=collection, tenant=tenant or "*", action=action)
            for action in actions
        ]


class RBAC:
    actions = ActionsFactory
    permissions = PermissionsFactory
