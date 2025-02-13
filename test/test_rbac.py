from weaviate.classes.rbac import Permissions


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
