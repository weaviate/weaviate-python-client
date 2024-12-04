import pytest

from integration.conftest import ClientFactory
from weaviate.auth import Auth
from weaviate.classes.rbac import Permissions, Actions
from weaviate.rbac.models import (
    Role,
    ClusterPermission,
    CollectionsPermission,
    DataPermission,
    RolesPermission,
    BackupsPermission,
    NodesPermission,
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
            ),
        ),
        (
            Permissions.roles(role="*", manage=True),
            Role(
                name="ManageAllRoles",
                cluster_permissions=[],
                users_permissions=[],
                collections_permissions=[],
                roles_permissions=[RolesPermission(role="*", action=Actions.Roles.MANAGE)],
                data_permissions=[],
                backups_permissions=[],
                nodes_permissions=[],
            ),
        ),
        (
            Permissions.collections(collection="Test", manage_collection=True),
            Role(
                name="ManageTestCollection",
                cluster_permissions=[],
                users_permissions=[],
                collections_permissions=[
                    CollectionsPermission(collection="Test", action=Actions.Collections.MANAGE)
                ],
                roles_permissions=[],
                data_permissions=[],
                backups_permissions=[],
                nodes_permissions=[],
            ),
        ),
        (
            Permissions.data(collection="Test", manage=True),
            Role(
                name="ManageTestData",
                cluster_permissions=[],
                users_permissions=[],
                collections_permissions=[],
                roles_permissions=[],
                data_permissions=[DataPermission(collection="Test", action=Actions.Data.MANAGE)],
                backups_permissions=[],
                nodes_permissions=[],
            ),
        ),
    ],
)
def test_create_role(client_factory: ClientFactory, permissions, expected) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 28, 0):
            pytest.skip("This test requires Weaviate 1.28.0 or higher")
        try:
            client.roles.create(
                name=expected.name,
                permissions=permissions,
            )
            role = client.roles.by_name(expected.name)
            assert role == expected
        finally:
            client.roles.delete(expected.name)


def test_add_permissions_to_existing(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 28, 0):
            pytest.skip("This test requires Weaviate 1.28.0 or higher")
        role_name = "ExistingRolePermissions"
        try:
            client.roles.create(
                name=role_name,
                permissions=Permissions.collections(collection="*", create_collection=True),
            )
            role = client.roles.by_name(role_name)

            assert role is not None
            assert role.collections_permissions is not None
            assert len(role.collections_permissions) == 1
            assert role.collections_permissions[0].action == Actions.Collections.CREATE

            client.roles.add_permissions(
                permissions=[
                    Permissions.collections(collection="*", delete_collection=True),
                ],
                role=role_name,
            )

            role = client.roles.by_name(role_name)
            assert role is not None
            assert role.collections_permissions is not None
            assert len(role.collections_permissions) == 2
            assert role.collections_permissions[0].action == Actions.Collections.CREATE
            assert role.collections_permissions[1].action == Actions.Collections.DELETE
        finally:
            client.roles.delete(role_name)


def test_upsert_permissions(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 28, 0):
            pytest.skip("This test requires Weaviate 1.28.0 or higher")
        role_name = "ExistingRoleUpsert"
        try:
            client.roles.add_permissions(
                permissions=Permissions.collections(collection="*", create_collection=True),
                role=role_name,
            )

            role = client.roles.by_name(role_name)
            assert role is not None
            assert role.collections_permissions is not None
            assert len(role.collections_permissions) == 1
            assert role.collections_permissions[0].action == Actions.Collections.CREATE
        finally:
            client.roles.delete(role_name)


def test_downsert_permissions(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 28, 0):
            pytest.skip("This test requires Weaviate 1.28.0 or higher")
        role_name = "ExistingRoleDownsert"
        try:
            client.roles.create(
                name=role_name,
                permissions=Permissions.collections(
                    collection="*", create_collection=True, delete_collection=True
                ),
            )

            role = client.roles.by_name(role_name)
            assert role is not None
            assert role.collections_permissions is not None
            assert len(role.collections_permissions) == 2
            assert role.collections_permissions[0].action == Actions.Collections.CREATE
            assert role.collections_permissions[1].action == Actions.Collections.DELETE

            client.roles.remove_permissions(
                permissions=Permissions.collections(collection="*", delete_collection=True),
                role=role_name,
            )

            role = client.roles.by_name(role_name)
            assert role is not None
            assert role.collections_permissions is not None
            assert len(role.collections_permissions) == 1
            assert role.collections_permissions[0].action == Actions.Collections.CREATE

            client.roles.remove_permissions(
                permissions=Permissions.collections(collection="*", create_collection=True),
                role=role_name,
            )
            role = client.roles.by_name(role_name)
            assert role is None
        finally:
            client.roles.delete(role_name)


def test_own_roles(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 28, 0):
            pytest.skip("This test requires Weaviate 1.28.0 or higher")
        roles = client.roles.get_current_roles()
        assert len(roles) > 0


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
                name=role_name,
                permissions=required_permissions,
            )

            role = client.roles.by_name(role_name)
            assert role is not None
            assert role.collections_permissions is not None
            assert len(role.collections_permissions) == 1
            assert role.collections_permissions[0].action == Actions.Collections.READ
            assert len(role.data_permissions) == 2
            assert role.data_permissions[0].action == Actions.Data.CREATE
            assert role.data_permissions[1].action == Actions.Data.UPDATE
        finally:
            client.roles.delete(role_name)
