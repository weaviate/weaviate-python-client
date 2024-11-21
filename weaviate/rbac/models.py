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


class CollectionsAction(str, _Action, Enum):
    CREATE = "create_schema"
    READ = "read_schema"
    UPDATE = "update_schema"
    DELETE = "delete_schema"

    @staticmethod
    def values() -> List[str]:
        return [action.value for action in CollectionsAction]


class ObjectsCollectionAction(str, _Action, Enum):
    CREATE = "create_data"
    READ = "read_data"
    UPDATE = "update_data"
    DELETE = "delete_data"

    @staticmethod
    def values() -> List[str]:
        return [action.value for action in ObjectsCollectionAction]


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
    tenant: str
    action: CollectionsAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
            "collection": self.collection,
            "role": "*",
            "tenant": self.tenant,
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


class _ObjectsCollectionPermission(_Permission):
    collection: str
    tenant: str
    action: ObjectsCollectionAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
            "collection": self.collection,
            "role": "*",
            "tenant": self.tenant,
            "user": "*",
        }


@dataclass
class CollectionsPermission:
    collection: str
    action: CollectionsAction
    tenant: str


@dataclass
class ObjectsCollectionPermission:
    collection: str
    action: ObjectsCollectionAction


@dataclass
class RolesPermission:
    role: str
    action: RolesAction


@dataclass
class UsersPermission:
    user: str
    action: UsersAction


@dataclass
class Role:
    name: str
    cluster_actions: Optional[List[ClusterAction]]
    collections_permissions: Optional[List[CollectionsPermission]]
    objects_collection_permissions: Optional[List[ObjectsCollectionPermission]]
    roles_permissions: Optional[List[RolesPermission]]
    users_permissions: Optional[List[UsersPermission]]

    @classmethod
    def _from_weaviate_role(cls, role: WeaviateRole) -> "Role":
        cluster_actions: List[ClusterAction] = []
        users_permissions: List[UsersPermission] = []
        collection_permissions: List[CollectionsPermission] = []
        roles_permissions: List[RolesPermission] = []
        objects_collection_permissions: List[ObjectsCollectionPermission] = []

        for permission in role["permissions"]:
            if permission["action"] in ClusterAction.values():
                cluster_actions.append(ClusterAction(permission["action"]))
            elif permission["action"] in UsersAction.values():
                users_permissions.append(
                    UsersPermission(
                        user=permission["user"], action=UsersAction(permission["action"])
                    )
                )
            elif permission["action"] in CollectionsAction.values():
                collection_permissions.append(
                    CollectionsPermission(
                        collection=permission["collection"],
                        tenant=permission.get("tenant", "*"),
                        action=CollectionsAction(permission["action"]),
                    )
                )
            elif permission["action"] in RolesAction.values():
                roles_permissions.append(
                    RolesPermission(
                        role=permission["role"], action=RolesAction(permission["action"])
                    )
                )
            elif permission["action"] in ObjectsCollectionAction.values():
                objects_collection_permissions.append(
                    ObjectsCollectionPermission(
                        collection=permission["collection"],
                        action=ObjectsCollectionAction(permission["action"]),
                    )
                )
            else:
                raise ValueError(
                    f"The actions of role {role['name']} are mixed between levels somehow!"
                )
        return cls(
            name=role["name"],
            cluster_actions=ca if len(ca := cluster_actions) > 0 else None,
            users_permissions=up if len(up := users_permissions) > 0 else None,
            collections_permissions=cp if len(cp := collection_permissions) > 0 else None,
            roles_permissions=rp if len(rp := roles_permissions) > 0 else None,
            objects_collection_permissions=(
                ocp if len(ocp := objects_collection_permissions) > 0 else None
            ),
        )


@dataclass
class User:
    name: str


Actions = Union[_Action, Sequence[_Action]]
Permissions = Union[_Permission, Sequence[_Permission]]


class _ObjectsCollectionFactory:
    @staticmethod
    def create(collection: str, tenant: str = "*") -> _ObjectsCollectionPermission:
        return _ObjectsCollectionPermission(
            collection=collection, action=ObjectsCollectionAction.CREATE, tenant=tenant
        )

    @staticmethod
    def read(collection: str, tenant: str = "*") -> _ObjectsCollectionPermission:
        return _ObjectsCollectionPermission(
            collection=collection, action=ObjectsCollectionAction.READ, tenant=tenant
        )

    @staticmethod
    def update(collection: str, tenant: str = "*") -> _ObjectsCollectionPermission:
        return _ObjectsCollectionPermission(
            collection=collection, action=ObjectsCollectionAction.UPDATE, tenant=tenant
        )

    @staticmethod
    def delete(collection: str, tenant: str = "*") -> _ObjectsCollectionPermission:
        return _ObjectsCollectionPermission(
            collection=collection, action=ObjectsCollectionAction.DELETE, tenant=tenant
        )


class _CollectionsFactory:
    objects = _ObjectsCollectionFactory

    @staticmethod
    def create(
        collection: Optional[str] = None, tenant: Optional[str] = None
    ) -> _CollectionsPermission:
        return _CollectionsPermission(
            collection=collection or "*", tenant=tenant or "*", action=CollectionsAction.CREATE
        )

    @staticmethod
    def read(
        collection: Optional[str] = None, tenant: Optional[str] = None
    ) -> _CollectionsPermission:
        return _CollectionsPermission(
            collection=collection or "*", tenant=tenant or "*", action=CollectionsAction.READ
        )

    @staticmethod
    def update(
        collection: Optional[str] = None, tenant: Optional[str] = None
    ) -> _CollectionsPermission:
        return _CollectionsPermission(
            collection=collection or "*", tenant=tenant or "*", action=CollectionsAction.UPDATE
        )

    @staticmethod
    def delete(
        collection: Optional[str] = None, tenant: Optional[str] = None
    ) -> _CollectionsPermission:
        return _CollectionsPermission(
            collection=collection or "*", tenant=tenant or "*", action=CollectionsAction.DELETE
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


class PermissionsFactory:
    cluser = _ClusterFactory
    collections = _CollectionsFactory
    roles = _RolesFactory
    users = _UsersFactory


class RBAC:
    actions = ActionsFactory
    permissions = PermissionsFactory
