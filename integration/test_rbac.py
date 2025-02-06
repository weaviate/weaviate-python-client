from typing import List
import pytest

from integration.conftest import ClientFactory
from weaviate.auth import Auth
from weaviate.classes.rbac import Permissions, Actions, RoleScope
from weaviate.rbac.models import (
    _InputPermission,
    Role,
    ClusterPermission,
    CollectionsPermission,
    DataPermission,
    RolesPermission,
    BackupsPermission,
    NodesPermission,
    TenantsPermission,
    UsersPermission,
)

RBAC_PORTS = (8092, 50063)
RBAC_AUTH_CREDS = Auth.api_key("existing-key")


@pytest.mark.parametrize(
    "permissions,expected",
    [
        (
            Permissions.backup(collection="Test", manage=True),
            Role(
                name="ManageAllBackups",
                cluster_permissions=[],
                users_permissions=[],
                collections_permissions=[],
                roles_permissions=[],
                data_permissions=[],
                backups_permissions=[
                    BackupsPermission(collection="Test", action=Actions.Backups.MANAGE)
                ],
                nodes_permissions=[],
                tenants_permissions=[],
            ),
        ),
        (
            Permissions.cluster(read=True),
            Role(
                name="ReadCluster",
                cluster_permissions=[ClusterPermission(action=Actions.Cluster.READ)],
                users_permissions=[],
                collections_permissions=[],
                roles_permissions=[],
                data_permissions=[],
                backups_permissions=[],
                nodes_permissions=[],
                tenants_permissions=[],
            ),
        ),
        (
            Permissions.collections(collection="Test", create_collection=True),
            Role(
                name="CreateAllCollections",
                cluster_permissions=[],
                users_permissions=[],
                collections_permissions=[
                    CollectionsPermission(collection="Test", action=Actions.Collections.CREATE)
                ],
                roles_permissions=[],
                data_permissions=[],
                backups_permissions=[],
                nodes_permissions=[],
                tenants_permissions=[],
            ),
        ),
        (
            Permissions.data(collection="*", create=True),
            Role(
                name="CreateAllData",
                cluster_permissions=[],
                users_permissions=[],
                collections_permissions=[],
                roles_permissions=[],
                data_permissions=[DataPermission(collection="*", action=Actions.Data.CREATE)],
                backups_permissions=[],
                nodes_permissions=[],
                tenants_permissions=[],
            ),
        ),
        (
            Permissions.nodes(collection="test", read=True, verbosity="minimal"),
            Role(
                name="MinimalNodes",
                cluster_permissions=[],
                users_permissions=[],
                collections_permissions=[],
                roles_permissions=[],
                data_permissions=[],
                backups_permissions=[],
                nodes_permissions=[
                    NodesPermission(verbosity="minimal", action=Actions.Nodes.READ, collection=None)
                ],
                tenants_permissions=[],
            ),
        ),
        (
            Permissions.nodes(verbosity="verbose", collection="Test", read=True),
            Role(
                name="VerboseNodes",
                cluster_permissions=[],
                users_permissions=[],
                collections_permissions=[],
                roles_permissions=[],
                data_permissions=[],
                backups_permissions=[],
                nodes_permissions=[
                    NodesPermission(
                        verbosity="verbose", action=Actions.Nodes.READ, collection="Test"
                    )
                ],
                tenants_permissions=[],
            ),
        ),
        (
            Permissions.roles(role="*", manage=True),
            Role(
                name="ManageAllRoles",
                cluster_permissions=[],
                users_permissions=[],
                collections_permissions=[],
                roles_permissions=[
                    RolesPermission(role="*", action=Actions.Roles.MANAGE, scope=RoleScope.MATCH)
                ],
                data_permissions=[],
                backups_permissions=[],
                nodes_permissions=[],
                tenants_permissions=[],
            ),
        ),
        (
            Permissions.tenants(collection="*", read=True),
            Role(
                name="TenantsReadRole",
                cluster_permissions=[],
                users_permissions=[],
                collections_permissions=[],
                roles_permissions=[],
                data_permissions=[],
                backups_permissions=[],
                nodes_permissions=[],
                tenants_permissions=[
                    TenantsPermission(collection="*", action=Actions.Tenants.READ)
                ],
            ),
        ),
        (
            Permissions.users(user="*", assign_and_revoke=True),
            Role(
                name="UserAssignRole",
                cluster_permissions=[],
                users_permissions=[
                    UsersPermission(user="*", action=Actions.Users.ASSIGN_AND_REVOKE)
                ],
                collections_permissions=[],
                roles_permissions=[],
                data_permissions=[],
                backups_permissions=[],
                nodes_permissions=[],
                tenants_permissions=[],
            ),
        ),
    ],
)
def test_create_role(
    client_factory: ClientFactory, permissions: List[_InputPermission], expected
) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 28, 0):
            pytest.skip("This test requires Weaviate 1.28.0 or higher")
        try:
            client.roles.delete(expected.name)
            client.roles.create(
                role_name=expected.name,
                permissions=permissions,
            )
            role = client.roles.get(expected.name)
            assert role is not None
            assert role == expected
            assert len(role.permissions) == 1
        finally:
            client.roles.delete(expected.name)


def test_add_permissions_to_existing(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 28, 0):
            pytest.skip("This test requires Weaviate 1.28.0 or higher")
        role_name = "ExistingRolePermissionsAdd"
        try:
            client.roles.create(
                role_name=role_name,
                permissions=Permissions.collections(collection="*", create_collection=True),
            )
            role = client.roles.get(role_name)

            assert role is not None
            assert role.collections_permissions is not None
            assert len(role.collections_permissions) == 1
            assert len(role.permissions) == 1
            assert role.collections_permissions[0].action == Actions.Collections.CREATE

            client.roles.add_permissions(
                permissions=[
                    Permissions.collections(collection="*", delete_collection=True),
                ],
                role_name=role_name,
            )

            role = client.roles.get(role_name)
            assert role is not None
            assert role.collections_permissions is not None
            assert len(role.collections_permissions) == 2
            assert len(role.permissions) == 2
            assert role.collections_permissions[0].action == Actions.Collections.CREATE
            assert role.collections_permissions[1].action == Actions.Collections.DELETE
        finally:
            client.roles.delete(role_name)


def test_remove_permissions_from_existing(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 28, 0):
            pytest.skip("This test requires Weaviate 1.28.0 or higher")
        role_name = "ExistingRolePermissionsRemove"
        try:
            client.roles.create(
                role_name=role_name,
                permissions=Permissions.collections(
                    collection="*", create_collection=True, delete_collection=True
                ),
            )
            role = client.roles.get(role_name)

            assert role is not None
            assert role.collections_permissions is not None
            assert len(role.collections_permissions) == 2
            assert len(role.permissions) == 2

            client.roles.remove_permissions(
                permissions=[
                    Permissions.collections(collection="*", delete_collection=True),
                ],
                role_name=role_name,
            )

            role = client.roles.get(role_name)
            assert role is not None
            assert role.collections_permissions is not None
            assert len(role.collections_permissions) == 1
            assert len(role.permissions) == 1
            assert role.collections_permissions[0].action == Actions.Collections.CREATE
        finally:
            client.roles.delete(role_name)


def test_multiple_permissions(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 28, 0):
            pytest.skip("This test requires Weaviate 1.28.0 or higher")
        role_name = "MultiplePermissions"
        try:
            required_permissions = [
                Permissions.data(collection="test", create=True, update=True),
                Permissions.collections(collection="test", read_config=True),
            ]

            client.roles.create(
                role_name=role_name,
                permissions=required_permissions,
            )

            role = client.roles.get(role_name)
            assert role is not None
            assert len(role.permissions) == 3
            assert role.collections_permissions is not None
            assert len(role.collections_permissions) == 1
            assert role.collections_permissions[0].action == Actions.Collections.READ
            assert len(role.data_permissions) == 2
            assert role.data_permissions[0].action == Actions.Data.CREATE
            assert role.data_permissions[1].action == Actions.Data.UPDATE

            assert client.roles.has_permissions(
                permissions=role.collections_permissions[0], role=role_name
            )
            assert client.roles.has_permissions(permissions=role.data_permissions, role=role_name)
            assert client.roles.has_permissions(
                permissions=required_permissions[1][0], role=role_name
            )
            assert client.roles.has_permissions(permissions=required_permissions[0], role=role_name)
            assert client.roles.has_permissions(permissions=required_permissions[1], role=role_name)
            assert client.roles.has_permissions(permissions=required_permissions, role=role_name)
        finally:
            client.roles.delete(role_name)


@pytest.mark.parametrize("scope", [RoleScope.ALL, RoleScope.MATCH])
def test_role_scope(client_factory: ClientFactory, scope: RoleScope) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 28, 4):
            pytest.skip("This test requires Weaviate 1.28.4 or higher")
        role_name = "role_permission_with_scope"
        try:
            client.roles.delete(role_name)
            client.roles.create(
                role_name=role_name,
                permissions=Permissions.roles(role="test", manage=scope),
            )

            role = client.roles.get(role_name)
            assert role is not None
            assert len(role.permissions) == 1
            assert role.roles_permissions[0].scope == scope
        finally:
            client.roles.delete(role_name)


def test_get_assigned_users(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 28, 0):
            pytest.skip("This test requires Weaviate 1.28.0 or higher")
        client.users.assign_roles(user_id="existing-user", role_names="viewer")
        assigned_users = client.roles.get_assigned_user_ids("viewer")
        assert len(assigned_users) == 1
        assert assigned_users[0] == "existing-user"
