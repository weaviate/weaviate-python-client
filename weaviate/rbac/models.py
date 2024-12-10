from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence, TypedDict, Union

from pydantic import BaseModel

from weaviate.cluster.types import Verbosity


class PermissionData(TypedDict):
    collection: str
    object: str  # noqa: A003
    tenant: str


class PermissionCollections(TypedDict):
    collection: str
    tenant: str


class PermissionNodes(TypedDict):
    collection: str
    verbosity: Verbosity


class PermissionBackup(TypedDict):
    collection: str


class PermissionRoles(TypedDict):
    role: str


# action is always present in WeaviatePermission
class WeaviatePermissionRequired(TypedDict):
    action: str


class WeaviatePermission(
    WeaviatePermissionRequired, total=False
):  # Add total=False to make all fields optional
    data: Optional[PermissionData]
    collections: Optional[PermissionCollections]
    nodes: Optional[PermissionNodes]
    backups: Optional[PermissionBackup]
    roles: Optional[PermissionRoles]


class WeaviateRole(TypedDict):
    name: str
    permissions: List[WeaviatePermission]


class _Action:
    pass


class CollectionsAction(str, _Action, Enum):
    CREATE = "create_collections"
    READ = "read_collections"
    UPDATE = "update_collections"
    DELETE = "delete_collections"
    MANAGE = "manage_collections"

    @staticmethod
    def values() -> List[str]:
        return [action.value for action in CollectionsAction]


class DataAction(str, _Action, Enum):
    CREATE = "create_data"
    READ = "read_data"
    UPDATE = "update_data"
    DELETE = "delete_data"
    MANAGE = "manage_data"

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


class _CollectionsPermission(_Permission):
    collection: str
    tenant: str
    action: CollectionsAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
            "collections": {
                "collection": self.collection,
                "tenant": self.tenant,
            },
        }


class _NodesPermission(_Permission):
    verbosity: Verbosity
    collection: str
    action: NodesAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
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
            "action": self.action,
            "roles": {
                "role": self.role,
            },
        }


class _UsersPermission(_Permission):
    action: UsersAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {"action": self.action}


class _BackupsPermission(_Permission):
    collection: str
    action: BackupsAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
            "backups": {
                "collection": self.collection,
            },
        }


class _ClusterPermission(_Permission):
    action: ClusterAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
        }


class _DataPermission(_Permission):
    collection: str
    tenant: str
    object_: str
    action: DataAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
            "data": {
                "collection": self.collection,
                "object": self.object_,
                "tenant": self.tenant,
            },
        }


@dataclass
class CollectionsPermission:
    collection: str
    action: CollectionsAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
            "collections": {
                "collection": self.collection,
                "tenant": "*",
            },
        }


@dataclass
class DataPermission:
    collection: str
    action: DataAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
            "data": {
                "collection": self.collection,
                "object": "*",
                "tenant": "*",
            },
        }


@dataclass
class RolesPermission:
    role: str
    action: RolesAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
            "roles": {
                "role": self.role,
            },
        }


@dataclass
class UsersPermission:
    action: UsersAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {"action": self.action}


@dataclass
class ClusterPermission:
    action: ClusterAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {"action": self.action}


@dataclass
class BackupsPermission:
    collection: str
    action: BackupsAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
            "backups": {
                "collection": self.collection,
            },
        }


@dataclass
class NodesPermission:
    collection: Optional[str]
    verbosity: Verbosity
    action: NodesAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
            "nodes": {
                "collection": self.collection or "*",
                "verbosity": self.verbosity,
            },
        }


PermissionsOutputType = Union[
    ClusterPermission,
    CollectionsPermission,
    DataPermission,
    RolesPermission,
    UsersPermission,
    BackupsPermission,
    NodesPermission,
]


@dataclass
class Role:
    name: str
    cluster_permissions: List[ClusterPermission]
    collections_permissions: List[CollectionsPermission]
    data_permissions: List[DataPermission]
    roles_permissions: List[RolesPermission]
    users_permissions: List[UsersPermission]
    backups_permissions: List[BackupsPermission]
    nodes_permissions: List[NodesPermission]

    @property
    def permissions(self) -> List[PermissionsOutputType]:
        permissions: List[PermissionsOutputType] = []
        permissions.extend(self.cluster_permissions)
        permissions.extend(self.collections_permissions)
        permissions.extend(self.data_permissions)
        permissions.extend(self.roles_permissions)
        permissions.extend(self.users_permissions)
        permissions.extend(self.backups_permissions)
        permissions.extend(self.nodes_permissions)
        return permissions

    @classmethod
    def _from_weaviate_role(cls, role: WeaviateRole) -> "Role":
        cluster_permissions: List[ClusterPermission] = []
        users_permissions: List[UsersPermission] = []
        collections_permissions: List[CollectionsPermission] = []
        roles_permissions: List[RolesPermission] = []
        data_permissions: List[DataPermission] = []
        backups_permissions: List[BackupsPermission] = []
        nodes_permissions: List[NodesPermission] = []

        for permission in role["permissions"]:
            if permission["action"] in ClusterAction.values():
                cluster_permissions.append(
                    ClusterPermission(action=ClusterAction(permission["action"]))
                )
            elif permission["action"] in UsersAction.values():
                users_permissions.append(UsersPermission(action=UsersAction(permission["action"])))
            elif permission["action"] in CollectionsAction.values():
                collections = permission.get("collections")
                if collections is not None:
                    collections_permissions.append(
                        CollectionsPermission(
                            collection=collections["collection"],
                            action=CollectionsAction(permission["action"]),
                        )
                    )
            elif permission["action"] in RolesAction.values():
                roles = permission.get("roles")
                if roles is not None:
                    roles_permissions.append(
                        RolesPermission(
                            role=roles["role"], action=RolesAction(permission["action"])
                        )
                    )
            elif permission["action"] in DataAction.values():
                data = permission.get("data")
                if data is not None:
                    data_permissions.append(
                        DataPermission(
                            collection=data["collection"],
                            action=DataAction(permission["action"]),
                        )
                    )
            elif permission["action"] in BackupsAction.values():
                backups = permission.get("backups")
                if backups is not None:
                    backups_permissions.append(
                        BackupsPermission(
                            collection=backups["collection"],
                            action=BackupsAction(permission["action"]),
                        )
                    )
            elif permission["action"] in NodesAction.values():
                nodes = permission.get("nodes")
                if nodes is not None:
                    nodes_permissions.append(
                        NodesPermission(
                            collection=nodes.get("collection"),
                            verbosity=nodes["verbosity"],
                            action=NodesAction(permission["action"]),
                        )
                    )
            else:
                raise ValueError(
                    f"The actions of role {role['name']} are mixed between levels somehow!"
                )
        return cls(
            name=role["name"],
            cluster_permissions=cluster_permissions,
            users_permissions=users_permissions,
            collections_permissions=collections_permissions,
            roles_permissions=roles_permissions,
            data_permissions=data_permissions,
            backups_permissions=backups_permissions,
            nodes_permissions=nodes_permissions,
        )


@dataclass
class User:
    name: str


ActionsType = Union[_Action, Sequence[_Action]]


PermissionsInputType = Union[
    _Permission,
    Sequence[_Permission],
    Sequence[Sequence[_Permission]],
    Sequence[Union[_Permission, Sequence[_Permission]]],
]
PermissionsCreateType = List[_Permission]


class _DataFactory:
    @staticmethod
    def create(*, collection: str) -> _DataPermission:
        return _DataPermission(
            collection=collection, tenant="*", object_="*", action=DataAction.CREATE
        )

    @staticmethod
    def read(*, collection: str) -> _DataPermission:
        return _DataPermission(
            collection=collection, tenant="*", object_="*", action=DataAction.READ
        )

    @staticmethod
    def update(*, collection: str) -> _DataPermission:
        return _DataPermission(
            collection=collection, tenant="*", object_="*", action=DataAction.UPDATE
        )

    @staticmethod
    def delete(*, collection: str) -> _DataPermission:
        return _DataPermission(
            collection=collection, tenant="*", object_="*", action=DataAction.DELETE
        )


class _CollectionsFactory:
    @staticmethod
    def create(*, collection: Optional[str] = None) -> _CollectionsPermission:
        return _CollectionsPermission(
            collection=collection or "*", tenant="*", action=CollectionsAction.CREATE
        )

    @staticmethod
    def read(*, collection: Optional[str] = None) -> _CollectionsPermission:
        return _CollectionsPermission(
            collection=collection or "*", tenant="*", action=CollectionsAction.READ
        )

    @staticmethod
    def update(*, collection: Optional[str] = None) -> _CollectionsPermission:
        return _CollectionsPermission(
            collection=collection or "*", tenant="*", action=CollectionsAction.UPDATE
        )

    @staticmethod
    def delete(*, collection: Optional[str] = None) -> _CollectionsPermission:
        return _CollectionsPermission(
            collection=collection or "*", tenant="*", action=CollectionsAction.DELETE
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
    def manage() -> _UsersPermission:
        return _UsersPermission(action=UsersAction.MANAGE)


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


class Actions:
    Data = DataAction
    Collections = CollectionsAction
    Roles = RolesAction
    Cluster = ClusterAction
    Nodes = NodesAction
    Backups = BackupsAction


class Permissions:

    @staticmethod
    def data(
        *,
        collection: Union[str, Sequence[str]],
        create: bool = False,
        read: bool = False,
        update: bool = False,
        delete: bool = False,
    ) -> PermissionsCreateType:
        permissions: List[_Permission] = []
        if isinstance(collection, str):
            collection = [collection]
        for c in collection:
            if create:
                permissions.append(_DataFactory.create(collection=c))
            if read:
                permissions.append(_DataFactory.read(collection=c))
            if update:
                permissions.append(_DataFactory.update(collection=c))
            if delete:
                permissions.append(_DataFactory.delete(collection=c))
        return permissions

    @staticmethod
    def collections(
        *,
        collection: Union[str, Sequence[str]],
        create_collection: bool = False,
        read_config: bool = False,
        update_config: bool = False,
        delete_collection: bool = False,
    ) -> PermissionsCreateType:
        permissions: List[_Permission] = []
        if isinstance(collection, str):
            collection = [collection]
        for c in collection:
            if create_collection:
                permissions.append(_CollectionsFactory.create(collection=c))
            if read_config:
                permissions.append(_CollectionsFactory.read(collection=c))
            if update_config:
                permissions.append(_CollectionsFactory.update(collection=c))
            if delete_collection:
                permissions.append(_CollectionsFactory.delete(collection=c))
        return permissions

    @staticmethod
    def roles(
        *, role: Union[str, Sequence[str]], read: bool = False, manage: bool = False
    ) -> PermissionsCreateType:
        permissions: List[_Permission] = []
        if isinstance(role, str):
            role = [role]
        for r in role:
            if read:
                permissions.append(_RolesFactory.read(role=r))
            if manage:
                permissions.append(_RolesFactory.manage(role=r))
        return permissions

    @staticmethod
    def backup(
        *, collection: Union[str, Sequence[str]], manage: bool = False
    ) -> PermissionsCreateType:
        permissions: List[_Permission] = []
        if isinstance(collection, str):
            collection = [collection]
        for c in collection:
            if manage:
                permissions.append(_BackupsFactory.manage(collection=c))
        return permissions

    @staticmethod
    def nodes(
        *,
        collection: Union[str, Sequence[str]],
        verbosity: Verbosity = "minimal",
        read: bool = False,
    ) -> PermissionsCreateType:
        permissions: List[_Permission] = []
        if isinstance(collection, str):
            collection = [collection]
        for c in collection:
            if read:
                permissions.append(_NodesFactory.read(collection=c, verbosity=verbosity))
        return permissions

    @staticmethod
    def cluster(*, read: bool = False) -> PermissionsCreateType:
        permissions: List[_Permission] = []
        if read:
            permissions.append(_ClusterFactory.read())
        return permissions
