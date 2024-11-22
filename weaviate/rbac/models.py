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


class ConfigAction(str, _Action, Enum):
    CREATE = "create_schema"
    READ = "read_schema"
    UPDATE = "update_schema"
    DELETE = "delete_schema"

    @staticmethod
    def values() -> List[str]:
        return [action.value for action in ConfigAction]


class DataAction(str, _Action, Enum):
    CREATE = "create_data"
    READ = "read_data"
    UPDATE = "update_data"
    DELETE = "delete_data"

    @staticmethod
    def values() -> List[str]:
        return [action.value for action in DataAction]


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


class _ConfigPermission(_Permission):
    collection: str
    tenant: str
    action: ConfigAction

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


class _DataPermission(_Permission):
    collection: str
    tenant: str
    action: DataAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
            "collection": self.collection,
            "role": "*",
            "tenant": self.tenant,
            "user": "*",
        }


@dataclass
class ConfigPermission:
    collection: str
    action: ConfigAction
    tenant: str


@dataclass
class DataPermission:
    collection: str
    action: DataAction


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
    config_permissions: Optional[List[ConfigPermission]]
    data_permissions: Optional[List[DataPermission]]
    roles_permissions: Optional[List[RolesPermission]]
    users_permissions: Optional[List[UsersPermission]]

    @classmethod
    def _from_weaviate_role(cls, role: WeaviateRole) -> "Role":
        cluster_actions: List[ClusterAction] = []
        users_permissions: List[UsersPermission] = []
        config_permissions: List[ConfigPermission] = []
        roles_permissions: List[RolesPermission] = []
        data_permissions: List[DataPermission] = []

        for permission in role["permissions"]:
            if permission["action"] in ClusterAction.values():
                cluster_actions.append(ClusterAction(permission["action"]))
            elif permission["action"] in UsersAction.values():
                users_permissions.append(
                    UsersPermission(
                        user=permission["user"], action=UsersAction(permission["action"])
                    )
                )
            elif permission["action"] in ConfigAction.values():
                config_permissions.append(
                    ConfigPermission(
                        collection=permission["collection"],
                        tenant=permission.get("tenant", "*"),
                        action=ConfigAction(permission["action"]),
                    )
                )
            elif permission["action"] in RolesAction.values():
                roles_permissions.append(
                    RolesPermission(
                        role=permission["role"], action=RolesAction(permission["action"])
                    )
                )
            elif permission["action"] in DataAction.values():
                data_permissions.append(
                    DataPermission(
                        collection=permission["collection"],
                        action=DataAction(permission["action"]),
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
            config_permissions=cp if len(cp := config_permissions) > 0 else None,
            roles_permissions=rp if len(rp := roles_permissions) > 0 else None,
            data_permissions=(dp if len(dp := data_permissions) > 0 else None),
        )


@dataclass
class User:
    name: str


Actions = Union[_Action, Sequence[_Action]]
Permissions = Union[_Permission, Sequence[_Permission]]


class _DataFactory:
    @staticmethod
    def create(collection: str, tenant: str = "*") -> _DataPermission:
        return _DataPermission(collection=collection, action=DataAction.CREATE, tenant=tenant)

    @staticmethod
    def read(collection: str, tenant: str = "*") -> _DataPermission:
        return _DataPermission(collection=collection, action=DataAction.READ, tenant=tenant)

    @staticmethod
    def update(collection: str, tenant: str = "*") -> _DataPermission:
        return _DataPermission(collection=collection, action=DataAction.UPDATE, tenant=tenant)

    @staticmethod
    def delete(collection: str, tenant: str = "*") -> _DataPermission:
        return _DataPermission(collection=collection, action=DataAction.DELETE, tenant=tenant)


class _ConfigFactory:
    @staticmethod
    def create(collection: Optional[str] = None, tenant: Optional[str] = None) -> _ConfigPermission:
        return _ConfigPermission(
            collection=collection or "*", tenant=tenant or "*", action=ConfigAction.CREATE
        )

    @staticmethod
    def read(collection: Optional[str] = None, tenant: Optional[str] = None) -> _ConfigPermission:
        return _ConfigPermission(
            collection=collection or "*", tenant=tenant or "*", action=ConfigAction.READ
        )

    @staticmethod
    def update(collection: Optional[str] = None, tenant: Optional[str] = None) -> _ConfigPermission:
        return _ConfigPermission(
            collection=collection or "*", tenant=tenant or "*", action=ConfigAction.UPDATE
        )

    @staticmethod
    def delete(collection: Optional[str] = None, tenant: Optional[str] = None) -> _ConfigPermission:
        return _ConfigPermission(
            collection=collection or "*", tenant=tenant or "*", action=ConfigAction.DELETE
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
    config = ConfigAction
    data = DataAction
    roles = RolesAction
    users = UsersAction


class PermissionsFactory:
    cluster = _ClusterFactory
    config = _ConfigFactory
    data = _DataFactory
    roles = _RolesFactory
    users = _UsersFactory


class RBAC:
    actions = ActionsFactory
    permissions = PermissionsFactory
