from weaviate.classes.rbac import Actions, Permissions
from weaviate.rbac.models import Role


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
