import pytest

from integration.conftest import ClientFactory
from weaviate.auth import Auth
from weaviate.rbac.models import GroupTypes, Role

RBAC_PORTS = (8092, 50063)
RBAC_AUTH_CREDS = Auth.api_key("admin-key")


def test_assign_and_get_group_roles_oidc(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 32, 0):
            pytest.skip("This test requires Weaviate 1.32.0 or higher")

        roles_to_assign = ["viewer", "admin"]
        group_id = "/assign-group"
        client.groups.oidc.revoke_roles(group_id=group_id, role_names=roles_to_assign)

        roles_base = client.groups.oidc.get_assigned_roles(
            group_id=group_id,
        )
        assert len(roles_base) == 0

        client.groups.oidc.assign_roles(group_id=group_id, role_names=roles_to_assign)

        roles = client.groups.oidc.get_assigned_roles(group_id=group_id, include_permissions=True)
        assert len(roles) == 2
        for role_name in roles_to_assign:
            assert role_name in roles
            assert isinstance(roles[role_name], Role)

        client.groups.oidc.revoke_roles(group_id=group_id, role_names=roles_to_assign)

        roles_base = client.groups.oidc.get_assigned_roles(
            group_id=group_id,
        )
        assert len(roles_base) == 0


def test_known_groups(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 32, 0):
            pytest.skip("This test requires Weaviate 1.32.0 or higher")

        group1 = "/known-group1"
        group2 = "/known-group2"
        client.groups.oidc.assign_roles(group_id=group1, role_names="viewer")
        client.groups.oidc.assign_roles(group_id=group2, role_names="viewer")

        groups = client.groups.oidc.get_known_group_names()
        assert len(groups) >= 2  # other tests may add groups
        assert group1 in groups
        assert group2 in groups

        client.groups.oidc.revoke_roles(group_id=group1, role_names="viewer")
        client.groups.oidc.revoke_roles(group_id=group2, role_names="viewer")

        groups = client.groups.oidc.get_known_group_names()
        assert len(groups) >= 0  # other tests may add groups
        assert group1 not in groups
        assert group2 not in groups


def test_get_group_assignments(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 32, 0):
            pytest.skip("This test requires Weaviate 1.32.0 or higher")

        role_name = "test_group_assignments_role"
        client.roles.delete(role_name=role_name)
        client.roles.create(role_name=role_name, permissions=[])

        group_assignments = client.roles.get_group_assignments(role_name=role_name)
        assert len(group_assignments) == 0

        client.groups.oidc.assign_roles(group_id="custom-group", role_names=role_name)
        client.groups.oidc.assign_roles(group_id="custom-group2", role_names=role_name)

        group_assignments = client.roles.get_group_assignments(role_name=role_name)
        assert len(group_assignments) == 2
        for group in group_assignments:
            assert group.group_id in ["custom-group", "custom-group2"]
            assert group.group_type == GroupTypes.OIDC

        client.groups.oidc.revoke_roles(group_id="custom-group", role_names=role_name)
        client.groups.oidc.revoke_roles(group_id="custom-group2", role_names=role_name)
