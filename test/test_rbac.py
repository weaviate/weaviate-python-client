from typing import Any, List

import pytest
from httpx import Response

from weaviate.classes.rbac import Actions, Permissions
from weaviate.exceptions import WeaviateUnsupportedFeatureError
from weaviate.rbac.executor import _RolesExecutor
from weaviate.rbac.models import Role
from weaviate.util import _ServerVersion


class _StubConnection:
    """Records POST payloads instead of sending them; only what the roles executor touches."""

    def __init__(self, version: str) -> None:
        self._weaviate_version = _ServerVersion.from_string(version)
        self.posted: List[Any] = []

    def post(self, path: str, weaviate_object: Any, **kwargs: Any) -> Response:
        self.posted.append(weaviate_object)
        return Response(201 if path == "/authz/roles" else 200, json={})


def test_permissions_roles_only_manage_false() -> None:
    permissions = Permissions.roles(read=False, role="*")
    assert len(permissions) == 0


def test_permissions_roles_only_manage_true() -> None:
    permissions = Permissions.roles(read=True, role="*")
    assert len(permissions) == 1
    assert len(permissions[0].actions) == 1


def test_permissions_roles() -> None:
    permissions = Permissions.roles(read=True, create=False, role="*")
    assert len(permissions) == 1
    assert len(permissions[0].actions) == 1


def test_permissions_backup_read() -> None:
    permissions = Permissions.backup(collection="books", read=True)
    assert [p._to_weaviate() for p in permissions] == [
        [{"action": "read_backups", "backups": {"collection": "Books"}}]
    ]


def test_role_parses_read_backups() -> None:
    role = Role._from_weaviate_role(
        {
            "name": "r",
            "permissions": [{"action": "read_backups", "backups": {"collection": "Books"}}],
        }
    )
    assert role.backups_permissions[0].actions == {Actions.Backups.READ}


def test_permissions_backup_roles_and_users_are_separate_permissions() -> None:
    # Each collection, role and user becomes its own permission carrying only its own key:
    # the server stores one resource per entity and rejects a mix within one permission.
    permissions = Permissions.backup(
        collection=["c1", "c2"], role=["r1", "r2"], user=["u1", "u2"], manage=True
    )
    assert [p._to_weaviate() for p in permissions] == [
        [{"action": "manage_backups", "backups": {"collection": "C1"}}],
        [{"action": "manage_backups", "backups": {"collection": "C2"}}],
        [{"action": "manage_backups", "backups": {"role": "r1"}}],
        [{"action": "manage_backups", "backups": {"role": "r2"}}],
        [{"action": "manage_backups", "backups": {"user": "u1"}}],
        [{"action": "manage_backups", "backups": {"user": "u2"}}],
    ]


def test_permissions_backup_without_target_sends_no_keys() -> None:
    # No target at all means no permission, so nothing is sent.
    assert Permissions.backup(manage=True) == []


def test_role_parses_backups_on_roles_and_users() -> None:
    role = Role._from_weaviate_role(
        {
            "name": "r",
            "permissions": [
                {"action": "manage_backups", "backups": {"role": "r1"}},
                {"action": "manage_backups", "backups": {"user": "u1"}},
                {"action": "manage_backups", "backups": {"collection": "*"}},
            ],
        }
    )
    assert [(p.collection, p.role, p.user) for p in role.backups_permissions] == [
        ("", "r1", None),
        ("", None, "u1"),
        ("*", None, None),
    ]


@pytest.mark.parametrize(
    "permissions",
    [
        Permissions.backup(role="r1", manage=True),
        Permissions.backup(user="u1", read=True),
        Permissions.backup(collection="c1", role="r1", manage=True),
    ],
    ids=["role", "user", "collection-and-role"],
)
def test_roles_executor_rejects_backup_principals_on_old_server(permissions: Any) -> None:
    # Before 1.42 the server ignores the role/user key and defaults the collection to "*",
    # so the request must never leave the client.
    conn = _StubConnection("1.41.5")
    roles = _RolesExecutor(conn)  # type: ignore[arg-type]
    with pytest.raises(WeaviateUnsupportedFeatureError, match="1.42.0"):
        roles.create(role_name="r", permissions=permissions)
    with pytest.raises(WeaviateUnsupportedFeatureError, match="1.42.0"):
        roles.add_permissions(role_name="r", permissions=permissions)
    assert conn.posted == []


def test_roles_executor_sends_backup_principals_on_new_server() -> None:
    conn = _StubConnection("1.42.0")
    roles = _RolesExecutor(conn)  # type: ignore[arg-type]
    roles.create(role_name="r", permissions=Permissions.backup(role="r1", manage=True))
    roles.add_permissions(role_name="r", permissions=Permissions.backup(user="u1", manage=True))
    assert conn.posted == [
        {"name": "r", "permissions": [{"action": "manage_backups", "backups": {"role": "r1"}}]},
        {"permissions": [{"action": "manage_backups", "backups": {"user": "u1"}}]},
    ]


def test_roles_executor_allows_collection_backup_permission_on_old_server() -> None:
    # Collection-scoped backup permissions predate the gate and must keep working.
    conn = _StubConnection("1.39.0")
    roles = _RolesExecutor(conn)  # type: ignore[arg-type]
    roles.create(role_name="r", permissions=Permissions.backup(collection="c1", manage=True))
    assert conn.posted == [
        {
            "name": "r",
            "permissions": [{"action": "manage_backups", "backups": {"collection": "C1"}}],
        }
    ]
