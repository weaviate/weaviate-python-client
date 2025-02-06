from abc import abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Generic, List, Optional, Sequence, Set, TypeVar, TypedDict, Union

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


ActionT = TypeVar("ActionT", bound=Enum)


class _Permission(BaseModel, Generic[ActionT]):
    action: Set[ActionT]

    @abstractmethod
    def _to_weaviate(self) -> List[WeaviatePermission]:
        raise NotImplementedError()


class _CollectionsPermission(_Permission[CollectionsAction]):
    collection: str
    tenant: str

    def _to_weaviate(self) -> List[WeaviatePermission]:
        return [
            {
                "action": action,
                "collections": {
                    "collection": _capitalize_first_letter(self.collection),
                    "tenant": self.tenant,
                },
            }
            for action in self.action
        ]


class _TenantsPermission(_Permission[TenantsAction]):
    collection: str

    def _to_weaviate(self) -> List[WeaviatePermission]:
        return [
            {
                "action": action,
                "tenants": {
                    "collection": _capitalize_first_letter(self.collection),
                    "tenant": "*",
                },
            }
            for action in self.action
        ]


class _NodesPermission(_Permission[NodesAction]):
    verbosity: Verbosity
    collection: str

    def _to_weaviate(self) -> List[WeaviatePermission]:
        return [
            {
                "action": action,
                "nodes": {
                    "collection": _capitalize_first_letter(self.collection),
                    "verbosity": self.verbosity,
                },
            }
            for action in self.action
        ]


class _RolesPermission(_Permission[RolesAction]):
    role: str
    scope: Optional[str] = None

    def _to_weaviate(self) -> List[WeaviatePermission]:
        roles: PermissionRoles = {"role": self.role}
        if self.scope is not None:
            roles["scope"] = self.scope
        return [
            {
                "action": action,
                "roles": roles,
            }
            for action in self.action
        ]


class _UsersPermission(_Permission[UsersAction]):
    users: str

    def _to_weaviate(self) -> List[WeaviatePermission]:
        return [{"action": action, "users": {"users": self.users}} for action in self.action]


class _BackupsPermission(_Permission[BackupsAction]):
    collection: str

    def _to_weaviate(self) -> List[WeaviatePermission]:
        return [
            {
                "action": action,
                "backups": {
                    "collection": _capitalize_first_letter(self.collection),
                },
            }
            for action in self.action
        ]


class _ClusterPermission(_Permission[ClusterAction]):

    def _to_weaviate(self) -> List[WeaviatePermission]:
        return [
            {
                "action": action,
            }
            for action in self.action
        ]


class _DataPermission(_Permission[DataAction]):
    collection: str

    def _to_weaviate(self) -> List[WeaviatePermission]:
        return [
            {
                "action": action,
                "data": {
                    "collection": _capitalize_first_letter(self.collection),
                },
            }
            for action in self.action
        ]


class CollectionsPermissionOutput(_CollectionsPermission):
    pass


class DataPermissionOutput(_DataPermission):
    pass


class RolesPermissionOutput(_RolesPermission):
    pass


class UsersPermissionOutput(_UsersPermission):
    pass


class ClusterPermissionOutput(_ClusterPermission):
    pass


class BackupsPermissionOutput(_BackupsPermission):
    pass


class NodesPermissionOutput(_NodesPermission):
    pass


class TenantsPermissionOutput(_TenantsPermission):
    pass


PermissionsOutputType = Union[
    ClusterPermissionOutput,
    CollectionsPermissionOutput,
    DataPermissionOutput,
    RolesPermissionOutput,
    UsersPermissionOutput,
    BackupsPermissionOutput,
    NodesPermissionOutput,
    TenantsPermissionOutput,
]


@dataclass
class Role:
    name: str
    cluster_permissions: List[ClusterPermissionOutput]
    collections_permissions: List[CollectionsPermissionOutput]
    data_permissions: List[DataPermissionOutput]
    roles_permissions: List[RolesPermissionOutput]
    users_permissions: List[UsersPermissionOutput]
    backups_permissions: List[BackupsPermissionOutput]
    nodes_permissions: List[NodesPermissionOutput]
    tenants_permissions: List[TenantsPermissionOutput]

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
        cluster_permissions: List[ClusterPermissionOutput] = []
        users_permissions: List[UsersPermissionOutput] = []
        collections_permissions: List[CollectionsPermissionOutput] = []
        roles_permissions: List[RolesPermissionOutput] = []
        data_permissions: List[DataPermissionOutput] = []
        backups_permissions: List[BackupsPermissionOutput] = []
        nodes_permissions: List[NodesPermissionOutput] = []
        tenants_permissions: List[TenantsPermissionOutput] = []

        for permission in role["permissions"]:
            if permission["action"] in ClusterAction.values():
                cluster_permissions.append(
                    ClusterPermissionOutput(action={ClusterAction(permission["action"])})
                )
            elif permission["action"] in UsersAction.values():
                users = permission.get("users")
                if users is not None:
                    users_permissions.append(
                        UsersPermissionOutput(
                            action={UsersAction(permission["action"])}, users=users["users"]
                        )
                    )
            elif permission["action"] in CollectionsAction.values():
                collections = permission.get("collections")
                if collections is not None:
                    collections_permissions.append(
                        CollectionsPermissionOutput(
                            collection=collections["collection"],
                            tenant=collections.get("tenant", "*"),
                            action={CollectionsAction(permission["action"])},
                        )
                    )
            elif permission["action"] in TenantsAction.values():
                tenants = permission.get("tenants")
                if tenants is not None:
                    tenants_permissions.append(
                        TenantsPermissionOutput(
                            collection=tenants["collection"],
                            action={TenantsAction(permission["action"])},
                        )
                    )
            elif permission["action"] in RolesAction.values():
                roles = permission.get("roles")
                if roles is not None:
                    scope = roles.get("scope")
                    roles_permissions.append(
                        RolesPermissionOutput(
                            role=roles["role"],
                            action={RolesAction(permission["action"])},
                            scope=RoleScope(scope) if scope else None,
                        )
                    )
            elif permission["action"] in DataAction.values():
                data = permission.get("data")
                if data is not None:
                    data_permissions.append(
                        DataPermissionOutput(
                            collection=data["collection"],
                            action={DataAction(permission["action"])},
                        )
                    )
            elif permission["action"] in BackupsAction.values():
                backups = permission.get("backups")
                if backups is not None:
                    backups_permissions.append(
                        BackupsPermissionOutput(
                            collection=backups["collection"],
                            action={BackupsAction(permission["action"])},
                        )
                    )
            elif permission["action"] in NodesAction.values():
                nodes = permission.get("nodes")
                if nodes is not None:
                    nodes_permissions.append(
                        NodesPermissionOutput(
                            collection=nodes.get("collection", "*"),
                            verbosity=nodes["verbosity"],
                            action={NodesAction(permission["action"])},
                        )
                    )
            else:
                _Warnings.unknown_permission_encountered(permission)

        # unify permissions with common resource
        for perm in cluster_permissions:
            cluster_permissions[0].action.add(perm.action.pop())

        return cls(
            name=role["name"],
            cluster_permissions=_unify_permissions(cluster_permissions),
            users_permissions=_unify_permissions(users_permissions),
            collections_permissions=_unify_permissions(collections_permissions),
            roles_permissions=_unify_permissions(roles_permissions),
            data_permissions=_unify_permissions(data_permissions),
            backups_permissions=_unify_permissions(backups_permissions),
            nodes_permissions=_unify_permissions(nodes_permissions),
            tenants_permissions=_unify_permissions(tenants_permissions),
        )


T = TypeVar("T", bound=_Permission)


def _unify_permissions(permissions: List[T]) -> List[T]:
    unified: Dict[str, int] = {}

    for i, perm in enumerate(permissions):
        resource = ""
        for field in perm.model_fields_set:
            if field == "action":
                continue
            resource += field + str(getattr(perm, field)) + "#"
        if resource in unified:
            permissions[unified[resource]].action.add(perm.action.pop())
        else:
            unified[resource] = i

    return_permission: List[T] = []
    for i in unified.values():
        return_permission.append(permissions[i])

    return return_permission


@dataclass
class User:
    user_id: str
    roles: Dict[str, Role]


ActionsType = Union[_Action, Sequence[_Action]]


PermissionsInputType = Union[
    _Permission,
    Sequence[_Permission],
    Sequence[Sequence[_Permission]],
    Sequence[Union[_Permission, Sequence[_Permission]]],
]
PermissionsCreateType = List[_Permission]


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
        permissions: List[_Permission] = []
        if isinstance(collection, str):
            collection = [collection]
        for c in collection:
            permission = _DataPermission(collection=c, action=set())

            if create:
                permission.action.add(DataAction.CREATE)
            if read:
                permission.action.add(DataAction.READ)
            if update:
                permission.action.add(DataAction.UPDATE)
            if delete:
                permission.action.add(DataAction.DELETE)

            if len(permission.action) > 0:
                permissions.append(permission)
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
            permission = _CollectionsPermission(collection=c, tenant="*", action=set())

            if create_collection:
                permission.action.add(CollectionsAction.CREATE)
            if read_config:
                permission.action.add(CollectionsAction.READ)
            if update_config:
                permission.action.add(CollectionsAction.UPDATE)
            if delete_collection:
                permission.action.add(CollectionsAction.DELETE)
            if len(permission.action) > 0:
                permissions.append(permission)
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
        permissions: List[_Permission] = []
        if isinstance(collection, str):
            collection = [collection]
        for c in collection:
            permission = _TenantsPermission(collection=c, action=set())
            if create:
                permission.action.add(TenantsAction.CREATE)
            if read:
                permission.action.add(TenantsAction.READ)
            if update:
                permission.action.add(TenantsAction.UPDATE)
            if delete:
                permission.action.add(TenantsAction.DELETE)

            if len(permission.action) > 0:
                permissions.append(permission)

        return permissions

    @staticmethod
    def roles(
        *,
        role: Union[str, Sequence[str]],
        read: bool = False,
        manage: Optional[Union[RoleScope, bool]] = None,
    ) -> PermissionsCreateType:
        permissions: List[_Permission] = []
        if isinstance(role, str):
            role = [role]
        for r in role:
            permission = _RolesPermission(role=r, action=set())
            if read:
                permission.action.add(RolesAction.READ)
            if manage is not None:
                permission.action.add(RolesAction.MANAGE)
                if isinstance(manage, RoleScope):
                    permission.scope = manage
            if len(permission.action) > 0:
                permissions.append(permission)

        return permissions

    @staticmethod
    def users(
        *, user: Union[str, Sequence[str]], assign_and_revoke: bool = False
    ) -> PermissionsCreateType:
        permissions: List[_Permission] = []
        if isinstance(user, str):
            user = [user]
        for u in user:
            permission = _UsersPermission(users=u, action=set())

            if assign_and_revoke:
                permission.action.add(UsersAction.ASSIGN_AND_REVOKE)

            if len(permission.action) > 0:
                permissions.append(permission)

        return permissions

    @staticmethod
    def backup(
        *, collection: Union[str, Sequence[str]], manage: bool = False
    ) -> PermissionsCreateType:
        permissions: List[_Permission] = []
        if isinstance(collection, str):
            collection = [collection]
        for c in collection:
            permission = _BackupsPermission(collection=c, action=set())

            if manage:
                permission.action.add(BackupsAction.MANAGE)
            if len(permission.action) > 0:
                permissions.append(permission)
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
            permission = _NodesPermission(collection=c, verbosity=verbosity, action=set())

            if read:
                permission.action.add(NodesAction.READ)
            if len(permission.action) > 0:
                permissions.append(permission)

        return permissions

    @staticmethod
    def cluster(*, read: bool = False) -> PermissionsCreateType:
        if read:
            return [_ClusterPermission(action={ClusterAction.READ})]
        return []
