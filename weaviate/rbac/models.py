from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence, TypedDict, Union

from pydantic import BaseModel

from weaviate.cluster.types import Verbosity


class PermissionBackup(TypedDict):
    collection: str


class PermissionNodes(TypedDict):
    collection: str
    verbosity: Verbosity


class WeaviatePermission(TypedDict):
    action: str
    backup: PermissionBackup
    collection: str
    # object: Optional[str] not used yet, needs to be named different because of shadowing `object`
    nodes: PermissionNodes
    role: str
    user: str
    tenant: str


def _permission_all(action: str) -> WeaviatePermission:
    return {
        "action": action,
        "backup": {"collection": "*"},
        "collection": "*",
        "nodes": {"collection": "*", "verbosity": "minimal"},
        "role": "*",
        "user": "*",
        "tenant": "*",
    }


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
    READ = "read_cluster"

    @staticmethod
    def values() -> List[str]:
        return [action.value for action in ClusterAction]


class NodesAction(str, _Action, Enum):
    READ = "read_nodes"

    @staticmethod
    def values() -> List[str]:
        return [action.value for action in NodesAction]


class BackupsAction(str, _Action, Enum):
    MANAGE = "manage_backups"

    @staticmethod
    def values() -> List[str]:
        return [action.value for action in BackupsAction]


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
            **_permission_all(self.action),
            "collection": self.collection,
            "tenant": self.tenant,
        }


class _NodesPermission(_Permission):
    verbosity: Verbosity
    collection: str
    action: NodesAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            **_permission_all(self.action),
            "nodes": {
                "collection": self.collection,
                "verbosity": self.verbosity,
            },
        }


class _RolesPermission(_Permission):
    role: str
    action: RolesAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            **_permission_all(self.action),
            "role": self.role,
        }


class _UsersPermission(_Permission):
    user: str
    action: UsersAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            **_permission_all(self.action),
            "user": self.user,
        }


class _BackupsPermission(_Permission):
    collection: str
    action: BackupsAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            **_permission_all(self.action),
            "backup": {
                "collection": self.collection,
            },
        }


class _ClusterPermission(_Permission):
    action: ClusterAction

    def _to_weaviate(self) -> WeaviatePermission:
        return _permission_all(self.action)


class _DataPermission(_Permission):
    collection: str
    tenant: str
    action: DataAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            **_permission_all(self.action),
            "collection": self.collection,
            "tenant": self.tenant,
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
class BackupsPermission:
    collection: str
    action: BackupsAction


@dataclass
class NodesPermission:
    collection: Optional[str]
    verbosity: Verbosity
    action: NodesAction


@dataclass
class Role:
    name: str
    cluster_actions: Optional[List[ClusterAction]]
    config_permissions: Optional[List[ConfigPermission]]
    data_permissions: Optional[List[DataPermission]]
    roles_permissions: Optional[List[RolesPermission]]
    users_permissions: Optional[List[UsersPermission]]
    backups_permissions: Optional[List[BackupsPermission]]
    nodes_permissions: Optional[List[NodesPermission]]

    @classmethod
    def _from_weaviate_role(cls, role: WeaviateRole) -> "Role":
        cluster_actions: List[ClusterAction] = []
        users_permissions: List[UsersPermission] = []
        config_permissions: List[ConfigPermission] = []
        roles_permissions: List[RolesPermission] = []
        data_permissions: List[DataPermission] = []
        backups_permissions: List[BackupsPermission] = []
        nodes_permissions: List[NodesPermission] = []

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
            elif permission["action"] in BackupsAction.values():
                backups_permissions.append(
                    BackupsPermission(
                        collection=permission["backup"]["collection"],
                        action=BackupsAction(permission["action"]),
                    )
                )
            elif permission["action"] in NodesAction.values():
                nodes_permissions.append(
                    NodesPermission(
                        collection=permission["nodes"].get("collection"),
                        verbosity=permission["nodes"]["verbosity"],
                        action=NodesAction(permission["action"]),
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
            data_permissions=dp if len(dp := data_permissions) > 0 else None,
            backups_permissions=bp if len(bp := backups_permissions) > 0 else None,
            nodes_permissions=np if len(np := nodes_permissions) > 0 else None,
        )


@dataclass
class User:
    name: str


Actions = Union[_Action, Sequence[_Action]]
Permissions = Union[_Permission, Sequence[_Permission]]


class _DataFactory:
    @staticmethod
    def create(*, collection: str) -> _DataPermission:
        return _DataPermission(collection=collection, action=DataAction.CREATE, tenant="*")

    @staticmethod
    def read(*, collection: str) -> _DataPermission:
        return _DataPermission(collection=collection, action=DataAction.READ, tenant="*")

    @staticmethod
    def update(*, collection: str) -> _DataPermission:
        return _DataPermission(collection=collection, action=DataAction.UPDATE, tenant="*")

    @staticmethod
    def delete(*, collection: str) -> _DataPermission:
        return _DataPermission(collection=collection, action=DataAction.DELETE, tenant="*")


class _ConfigFactory:
    @staticmethod
    def create(*, collection: Optional[str] = None) -> _ConfigPermission:
        return _ConfigPermission(
            collection=collection or "*", tenant="*", action=ConfigAction.CREATE
        )

    @staticmethod
    def read(*, collection: Optional[str] = None) -> _ConfigPermission:
        return _ConfigPermission(collection=collection or "*", tenant="*", action=ConfigAction.READ)

    @staticmethod
    def update(*, collection: Optional[str] = None) -> _ConfigPermission:
        return _ConfigPermission(
            collection=collection or "*", tenant="*", action=ConfigAction.UPDATE
        )

    @staticmethod
    def delete(*, collection: Optional[str] = None) -> _ConfigPermission:
        return _ConfigPermission(
            collection=collection or "*", tenant="*", action=ConfigAction.DELETE
        )


class _RolesFactory:
    @staticmethod
    def manage(*, role: Optional[str] = None) -> _RolesPermission:
        return _RolesPermission(role=role or "*", action=RolesAction.MANAGE)

    @staticmethod
    def read(*, role: Optional[str] = None) -> _RolesPermission:
        return _RolesPermission(role=role or "*", action=RolesAction.READ)


class _UsersFactory:
    @staticmethod
    def manage(*, user: Optional[str] = None) -> _UsersPermission:
        return _UsersPermission(user=user or "*", action=UsersAction.MANAGE)


class _ClusterFactory:
    @staticmethod
    def read() -> _ClusterPermission:
        return _ClusterPermission(action=ClusterAction.READ)


class _NodesFactory:
    @staticmethod
    def read(
        *, collection: Optional[str] = None, verbosity: Verbosity = "minimal"
    ) -> _NodesPermission:
        return _NodesPermission(
            collection=collection or "*", action=NodesAction.READ, verbosity=verbosity
        )


class _BackupsFactory:
    @staticmethod
    def manage(*, collection: Optional[str] = None) -> _BackupsPermission:
        return _BackupsPermission(collection=collection or "*", action=BackupsAction.MANAGE)


class ActionsFactory:
    backups = BackupsAction
    cluster = ClusterAction
    config = ConfigAction
    data = DataAction
    nodes = NodesAction
    roles = RolesAction
    users = UsersAction


class PermissionsFactory:
    backups = _BackupsFactory
    cluster = _ClusterFactory
    config = _ConfigFactory
    data = _DataFactory
    nodes = _NodesFactory
    roles = _RolesFactory
    users = _UsersFactory


class RBAC:
    actions = ActionsFactory
    permissions = PermissionsFactory
