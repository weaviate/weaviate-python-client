from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Sequence, TypedDict, Union

from pydantic import BaseModel
from typing_extensions import NotRequired

from weaviate.cluster.types import Verbosity
from weaviate.str_enum import BaseEnum
from weaviate.util import _capitalize_first_letter


from weaviate.warnings import _Warnings


class RoleScope(str, BaseEnum):
    """Scope of the role permission."""

    MATCH = "match"
    ALL = "all"


class PermissionData(TypedDict):
    collection: str
    object: str  # noqa: A003
    tenant: str


class PermissionCollections(TypedDict):
    collection: str
    tenant: str


class PermissionsTenants(TypedDict):
    collection: str
    tenant: str


class PermissionNodes(TypedDict):
    collection: str
    verbosity: Verbosity


class PermissionBackup(TypedDict):
    collection: str


class PermissionRoles(TypedDict):
    role: str
    scope: NotRequired[str]


class PermissionsUsers(TypedDict):
    users: str


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
    tenants: Optional[PermissionsTenants]
    users: Optional[PermissionsUsers]


class WeaviateRole(TypedDict):
    name: str
    permissions: List[WeaviatePermission]


class WeaviateUser(TypedDict):
    username: str
    roles: List[WeaviateRole]
    groups: List[str]


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


class TenantsAction(str, _Action, Enum):
    CREATE = "create_tenants"
    READ = "read_tenants"
    UPDATE = "update_tenants"
    DELETE = "delete_tenants"

    @staticmethod
    def values() -> List[str]:
        return [action.value for action in TenantsAction]


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
    ASSIGN_AND_REVOKE = "assign_and_revoke_users"

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


class _InputPermission(BaseModel):
    @abstractmethod
    def _to_weaviate(self) -> WeaviatePermission:
        raise NotImplementedError()


class _CollectionsPermission(_InputPermission):
    collection: str
    tenant: str
    action: CollectionsAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
            "collections": {
                "collection": _capitalize_first_letter(self.collection),
                "tenant": self.tenant,
            },
        }


class _TenantsPermission(_InputPermission):
    collection: str
    action: TenantsAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
            "tenants": {
                "collection": _capitalize_first_letter(self.collection),
                "tenant": "*",
            },
        }


class _NodesPermission(_InputPermission):
    verbosity: Verbosity
    collection: str
    action: NodesAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
            "nodes": {
                "collection": _capitalize_first_letter(self.collection),
                "verbosity": self.verbosity,
            },
        }


class _RolesPermission(_InputPermission):
    role: str
    scope: Optional[str] = None
    action: RolesAction

    def _to_weaviate(self) -> WeaviatePermission:
        roles: PermissionRoles = {"role": self.role}
        if self.scope is not None:
            roles["scope"] = self.scope
        return {
            "action": self.action,
            "roles": roles,
        }


class _UsersPermission(_InputPermission):
    action: UsersAction
    users: str

    def _to_weaviate(self) -> WeaviatePermission:
        return {"action": self.action, "users": {"users": self.users}}


class _BackupsPermission(_InputPermission):
    collection: str
    action: BackupsAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
            "backups": {
                "collection": _capitalize_first_letter(self.collection),
            },
        }


class _ClusterPermission(_InputPermission):
    action: ClusterAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
        }


class _DataPermission(_InputPermission):
    collection: str
    tenant: str
    object_: str
    action: DataAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
            "data": {
                "collection": _capitalize_first_letter(self.collection),
                "object": self.object_,
                "tenant": self.tenant,
            },
        }


class _OutputPermission:
    @abstractmethod
    def _to_weaviate(self) -> WeaviatePermission:
        raise NotImplementedError()


@dataclass
class CollectionsPermission(_OutputPermission):
    collection: str
    action: CollectionsAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
            "collections": {
                "collection": _capitalize_first_letter(self.collection),
                "tenant": "*",
            },
        }


@dataclass
class DataPermission(_OutputPermission):
    collection: str
    action: DataAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
            "data": {
                "collection": _capitalize_first_letter(self.collection),
                "object": "*",
                "tenant": "*",
            },
        }


@dataclass
class RolesPermission(_OutputPermission):
    role: str
    action: RolesAction
    scope: Optional[RoleScope]

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
            "roles": {
                "role": self.role,
            },
        }


@dataclass
class UsersPermission(_OutputPermission):
    action: UsersAction
    user: str

    def _to_weaviate(self) -> WeaviatePermission:
        return {"action": self.action, "users": {"users": self.user}}


@dataclass
class ClusterPermission(_OutputPermission):
    action: ClusterAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {"action": self.action}


@dataclass
class BackupsPermission(_OutputPermission):
    collection: str
    action: BackupsAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
            "backups": {
                "collection": _capitalize_first_letter(self.collection),
            },
        }


@dataclass
class NodesPermission(_OutputPermission):
    collection: Optional[str]
    verbosity: Verbosity
    action: NodesAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
            "nodes": {
                "collection": _capitalize_first_letter(self.collection or "*"),
                "verbosity": self.verbosity,
            },
        }


@dataclass
class TenantsPermission(_OutputPermission):
    collection: str
    action: TenantsAction

    def _to_weaviate(self) -> WeaviatePermission:
        return {
            "action": self.action,
            "tenants": {
                "collection": _capitalize_first_letter(self.collection),
                "tenant": "*",
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
    TenantsPermission,
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
    tenants_permissions: List[TenantsPermission]

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
        permissions.extend(self.tenants_permissions)
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
        tenants_permissions: List[TenantsPermission] = []

        for permission in role["permissions"]:
            if permission["action"] in ClusterAction.values():
                cluster_permissions.append(
                    ClusterPermission(action=ClusterAction(permission["action"]))
                )
            elif permission["action"] in UsersAction.values():
                users = permission.get("users")
                if users is not None:
                    users_permissions.append(
                        UsersPermission(
                            action=UsersAction(permission["action"]), user=users["users"]
                        )
                    )
            elif permission["action"] in CollectionsAction.values():
                collections = permission.get("collections")
                if collections is not None:
                    collections_permissions.append(
                        CollectionsPermission(
                            collection=collections["collection"],
                            action=CollectionsAction(permission["action"]),
                        )
                    )
            elif permission["action"] in TenantsAction.values():
                tenants = permission.get("tenants")
                if tenants is not None:
                    tenants_permissions.append(
                        TenantsPermission(
                            collection=tenants["collection"],
                            action=TenantsAction(permission["action"]),
                        )
                    )
            elif permission["action"] in RolesAction.values():
                roles = permission.get("roles")
                if roles is not None:
                    scope = roles.get("scope")
                    roles_permissions.append(
                        RolesPermission(
                            role=roles["role"],
                            action=RolesAction(permission["action"]),
                            scope=RoleScope(scope) if scope else None,
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
                _Warnings.unknown_permission_encountered(permission)

        return cls(
            name=role["name"],
            cluster_permissions=cluster_permissions,
            users_permissions=users_permissions,
            collections_permissions=collections_permissions,
            roles_permissions=roles_permissions,
            data_permissions=data_permissions,
            backups_permissions=backups_permissions,
            nodes_permissions=nodes_permissions,
            tenants_permissions=tenants_permissions,
        )


@dataclass
class User:
    user_id: str
    roles: Dict[str, Role]


ActionsType = Union[_Action, Sequence[_Action]]


PermissionsInputType = Union[
    _InputPermission,
    Sequence[_InputPermission],
    Sequence[Sequence[_InputPermission]],
    Sequence[Union[_InputPermission, Sequence[_InputPermission]]],
]
PermissionsCreateType = List[_InputPermission]


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


class _TenantsFactory:
    @staticmethod
    def create(*, collection: Optional[str] = None) -> _TenantsPermission:
        return _TenantsPermission(collection=collection or "*", action=TenantsAction.CREATE)

    @staticmethod
    def read(*, collection: Optional[str] = None) -> _TenantsPermission:
        return _TenantsPermission(collection=collection or "*", action=TenantsAction.READ)

    @staticmethod
    def update(*, collection: Optional[str] = None) -> _TenantsPermission:
        return _TenantsPermission(collection=collection or "*", action=TenantsAction.UPDATE)

    @staticmethod
    def delete(*, collection: Optional[str] = None) -> _TenantsPermission:
        return _TenantsPermission(collection=collection or "*", action=TenantsAction.DELETE)


class _RolesFactory:
    @staticmethod
    def manage(*, role: Optional[str] = None, scope: Optional[str] = None) -> _RolesPermission:
        return _RolesPermission(role=role or "*", action=RolesAction.MANAGE, scope=scope)

    @staticmethod
    def read(*, role: Optional[str] = None) -> _RolesPermission:
        return _RolesPermission(role=role or "*", action=RolesAction.READ)


class _UsersFactory:
    @staticmethod
    def assign_and_revoke(user: str) -> _UsersPermission:
        return _UsersPermission(action=UsersAction.ASSIGN_AND_REVOKE, users=user)


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
    Tenants = TenantsAction
    Users = UsersAction


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
        permissions: List[_InputPermission] = []
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
        permissions: List[_InputPermission] = []
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
    def tenants(
        *,
        collection: Union[str, Sequence[str]],
        create: bool = False,
        read: bool = False,
        update: bool = False,
        delete: bool = False,
    ) -> PermissionsCreateType:
        permissions: List[_InputPermission] = []
        if isinstance(collection, str):
            collection = [collection]
        for c in collection:
            if create:
                permissions.append(_TenantsFactory.create(collection=c))
            if read:
                permissions.append(_TenantsFactory.read(collection=c))
            if update:
                permissions.append(_TenantsFactory.update(collection=c))
            if delete:
                permissions.append(_TenantsFactory.delete(collection=c))
        return permissions

    @staticmethod
    def roles(
        *,
        role: Union[str, Sequence[str]],
        read: bool = False,
        manage: Optional[Union[RoleScope, bool]] = None,
    ) -> PermissionsCreateType:
        permissions: List[_InputPermission] = []
        if isinstance(role, str):
            role = [role]
        for r in role:
            if read:
                permissions.append(_RolesFactory.read(role=r))
            if manage is not None:
                if isinstance(manage, bool):
                    permissions.append(_RolesFactory.manage(role=r))
                else:
                    permissions.append(_RolesFactory.manage(role=r, scope=manage))
        return permissions

    @staticmethod
    def users(
        *, user: Union[str, Sequence[str]], assign_and_revoke: bool = False
    ) -> PermissionsCreateType:
        permissions: List[_InputPermission] = []
        if isinstance(user, str):
            user = [user]
        for u in user:
            if assign_and_revoke:
                permissions.append(_UsersFactory.assign_and_revoke(user=u))
        return permissions

    @staticmethod
    def backup(
        *, collection: Union[str, Sequence[str]], manage: bool = False
    ) -> PermissionsCreateType:
        permissions: List[_InputPermission] = []
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
        permissions: List[_InputPermission] = []
        if isinstance(collection, str):
            collection = [collection]
        for c in collection:
            if read:
                permissions.append(_NodesFactory.read(collection=c, verbosity=verbosity))
        return permissions

    @staticmethod
    def cluster(*, read: bool = False) -> PermissionsCreateType:
        permissions: List[_InputPermission] = []
        if read:
            permissions.append(_ClusterFactory.read())
        return permissions
