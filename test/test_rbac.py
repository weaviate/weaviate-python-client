import pytest

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


@pytest.mark.parametrize(
    "read,manage,expected_actions",
    [
        (False, False, set()),
        (True, False, {"read_backups"}),
        (False, True, {"manage_backups"}),
        (True, True, {"read_backups", "manage_backups"}),
    ],
)
def test_backup_permissions_actions(read: bool, manage: bool, expected_actions: set[str]) -> None:
    permissions = Permissions.backup(collection="test", read=read, manage=manage)
    serialized = [entry for permission in permissions for entry in permission._to_weaviate()]
    assert {entry["action"] for entry in serialized} == expected_actions
    assert all(entry["backups"] == {"collection": "Test"} for entry in serialized)
    assert len(permissions) == bool(expected_actions)


def test_backup_read_permissions_multiple_collections() -> None:
    permissions = Permissions.backup(collection=["books", "*"], read=True)
    assert [permission._to_weaviate() for permission in permissions] == [
        [{"action": "read_backups", "backups": {"collection": "Books"}}],
        [{"action": "read_backups", "backups": {"collection": "*"}}],
    ]


@pytest.mark.parametrize(
    "actions",
    [["read_backups"], ["manage_backups"], ["read_backups", "manage_backups"]],
)
def test_backup_permissions_role_round_trip(actions: list[str]) -> None:
    role = Role._from_weaviate_role(
        {
            "name": "BackupReader",
            "permissions": [
                {"action": action, "backups": {"collection": "Books"}} for action in actions
            ],
        }
    )
    assert len(role.backups_permissions) == 1
    assert role.backups_permissions[0].collection == "Books"
    assert role.backups_permissions[0].actions == {Actions.Backups(action) for action in actions}
    serialized = [entry for permission in role.permissions for entry in permission._to_weaviate()]
    assert {entry["action"] for entry in serialized} == set(actions)
