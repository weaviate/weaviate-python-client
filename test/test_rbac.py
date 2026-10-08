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
