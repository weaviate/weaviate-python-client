from weaviate.classes.rbac import Actions, Permissions
from weaviate.namespaces.models import Namespace
from weaviate.rbac.models import (
    NamespacesAction,
    NamespacesPermissionOutput,
    Role,
    WeaviateRole,
    _NamespacesPermission,
)
from weaviate.users.users import UserDB, UserTypes


# --- Permissions.namespaces() factory ---


def test_namespaces_permission_no_actions() -> None:
    permissions = Permissions.namespaces(namespace="ns1")
    assert len(permissions) == 0


def test_namespaces_permission_manage() -> None:
    permissions = Permissions.namespaces(namespace="ns1", manage=True)
    assert len(permissions) == 1
    assert NamespacesAction.MANAGE in permissions[0].actions


def test_namespaces_permission_wildcard() -> None:
    permissions = Permissions.namespaces(namespace="*", manage=True)
    assert len(permissions) == 1
    assert isinstance(permissions[0], _NamespacesPermission)
    assert permissions[0].namespace == "*"


def test_namespaces_permission_multiple_namespaces() -> None:
    permissions = Permissions.namespaces(namespace=["ns1", "ns2"], manage=True)
    assert len(permissions) == 2
    ns_names = {p.namespace for p in permissions if isinstance(p, _NamespacesPermission)}
    assert ns_names == {"ns1", "ns2"}


# --- _to_weaviate() serialization ---


def test_namespaces_permission_to_weaviate() -> None:
    permissions = Permissions.namespaces(namespace="myns", manage=True)
    assert isinstance(permissions[0], _NamespacesPermission)
    wv = permissions[0]._to_weaviate()
    assert len(wv) == 1
    assert wv[0]["action"] == "manage_namespaces"
    assert wv[0].get("namespaces") == {"namespace": "myns"}


def test_namespaces_permission_to_weaviate_wildcard() -> None:
    permissions = Permissions.namespaces(namespace="*", manage=True)
    assert isinstance(permissions[0], _NamespacesPermission)
    wv = permissions[0]._to_weaviate()
    assert wv[0].get("namespaces") == {"namespace": "*"}


# --- Role._from_weaviate_role() parsing ---


def test_role_from_weaviate_role_parses_namespace_permission() -> None:
    weaviate_role: WeaviateRole = {
        "name": "ns-role",
        "permissions": [
            {"action": "manage_namespaces", "namespaces": {"namespace": "customer1"}},
        ],
    }
    role = Role._from_weaviate_role(weaviate_role)
    assert role.name == "ns-role"
    assert len(role.namespaces_permissions) == 1
    perm = role.namespaces_permissions[0]
    assert perm.namespace == "customer1"
    assert NamespacesAction.MANAGE in perm.actions


def test_role_from_weaviate_role_joins_namespace_permissions() -> None:
    weaviate_role: WeaviateRole = {
        "name": "ns-role",
        "permissions": [
            {"action": "manage_namespaces", "namespaces": {"namespace": "ns1"}},
            {"action": "manage_namespaces", "namespaces": {"namespace": "ns1"}},
        ],
    }
    role = Role._from_weaviate_role(weaviate_role)
    # Duplicate permissions on same resource should be collapsed
    assert len(role.namespaces_permissions) == 1


def test_role_from_weaviate_role_namespace_in_permissions_list() -> None:
    weaviate_role: WeaviateRole = {
        "name": "ns-role",
        "permissions": [
            {"action": "manage_namespaces", "namespaces": {"namespace": "*"}},
        ],
    }
    role = Role._from_weaviate_role(weaviate_role)
    assert isinstance(role.permissions[0], NamespacesPermissionOutput)


# --- Actions enum ---


def test_actions_namespaces_enum_accessible() -> None:
    assert Actions.Namespaces is NamespacesAction
    assert Actions.Namespaces.MANAGE.value == "manage_namespaces"


# --- Namespace model ---


def test_namespace_optional_fields_default_to_none() -> None:
    ns = Namespace(name="customer1")
    assert ns.name == "customer1"
    assert ns.home_node is None
    assert ns.state is None


def test_namespace_all_fields_set() -> None:
    ns = Namespace(name="customer1", home_node="node1", state="active")
    assert ns.name == "customer1"
    assert ns.home_node == "node1"
    assert ns.state == "active"


# --- UserDB.namespace field ---


def test_userdb_namespace_field_defaults_to_none() -> None:
    user = UserDB(
        user_id="u1",
        role_names=[],
        user_type=UserTypes.DB_DYNAMIC,
        active=True,
    )
    assert user.namespace is None


def test_userdb_namespace_field_set() -> None:
    user = UserDB(
        user_id="ns1:u1",
        role_names=[],
        user_type=UserTypes.DB_DYNAMIC,
        active=True,
        namespace="ns1",
    )
    assert user.namespace == "ns1"
