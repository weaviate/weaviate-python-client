from typing import Generator, List, Callable
import pytest
import weaviate
from integration.conftest import ClientFactory
from weaviate.auth import Auth
from weaviate.rbac.models import (
    RBAC,
    Role,
    ConfigPermission,
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
            RBAC.permissions.backups.manage(collection="Test"),
            Role(
                name="ManageAllBackups",
                cluster_actions=None,
                users_permissions=None,
                config_permissions=None,
                roles_permissions=None,
                data_permissions=None,
                backups_permissions=[
                    BackupsPermission(collection="Test", action=RBAC.actions.backups.MANAGE)
                ],
                nodes_permissions=None,
            ),
        ),
        (
            RBAC.permissions.cluster.read(),
            Role(
                name="ReadCluster",
                cluster_actions=[RBAC.actions.cluster.READ],
                users_permissions=None,
                config_permissions=None,
                roles_permissions=None,
                data_permissions=None,
                backups_permissions=None,
                nodes_permissions=None,
            ),
        ),
        (
            RBAC.permissions.config.create(),
            Role(
                name="CreateAllCollections",
                cluster_actions=None,
                users_permissions=None,
                config_permissions=[
                    ConfigPermission(collection="*", action=RBAC.actions.config.CREATE, tenant="*")
                ],
                roles_permissions=None,
                data_permissions=None,
                backups_permissions=None,
                nodes_permissions=None,
            ),
        ),
        (
            RBAC.permissions.data.create(collection="*"),
            Role(
                name="CreateAllData",
                cluster_actions=None,
                users_permissions=None,
                config_permissions=None,
                roles_permissions=None,
                data_permissions=[DataPermission(collection="*", action=RBAC.actions.data.CREATE)],
                backups_permissions=None,
                nodes_permissions=None,
            ),
        ),
        (
            RBAC.permissions.nodes.read(verbosity="minimal"),
            Role(
                name="MinimalNodes",
                cluster_actions=None,
                users_permissions=None,
                config_permissions=None,
                roles_permissions=None,
                data_permissions=None,
                backups_permissions=None,
                nodes_permissions=[
                    NodesPermission(
                        verbosity="minimal", action=RBAC.actions.nodes.READ, collection=None
                    )
                ],
            ),
        ),
        (
            RBAC.permissions.nodes.read(verbosity="verbose", collection="Test"),
            Role(
                name="VerboseNodes",
                cluster_actions=None,
                users_permissions=None,
                config_permissions=None,
                roles_permissions=None,
                data_permissions=None,
                backups_permissions=None,
                nodes_permissions=[
                    NodesPermission(
                        verbosity="verbose", action=RBAC.actions.nodes.READ, collection="Test"
                    )
                ],
            ),
        ),
        (
            RBAC.permissions.roles.manage(),
            Role(
                name="ManageAllRoles",
                cluster_actions=None,
                users_permissions=None,
                config_permissions=None,
                roles_permissions=[RolesPermission(role="*", action=RBAC.actions.roles.MANAGE)],
                data_permissions=None,
                backups_permissions=None,
                nodes_permissions=None,
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
                permissions=[
                    RBAC.permissions.config.create(),
                ],
            )
            role = client.roles.by_name(role_name)

            assert role is not None
            assert role.config_permissions is not None
            assert len(role.config_permissions) == 1
            assert role.config_permissions[0].action == RBAC.actions.config.CREATE

            client.roles.add_permissions(
                permissions=[
                    RBAC.permissions.config.delete(),
                ],
                role=role_name,
            )

            role = client.roles.by_name(role_name)
            assert role is not None
            assert role.config_permissions is not None
            assert len(role.config_permissions) == 2
            assert role.config_permissions[0].action == RBAC.actions.config.CREATE
            assert role.config_permissions[1].action == RBAC.actions.config.DELETE
        finally:
            client.roles.delete(role_name)


def test_upsert_permissions(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 28, 0):
            pytest.skip("This test requires Weaviate 1.28.0 or higher")
        role_name = "ExistingRoleUpsert"
        try:
            client.roles.add_permissions(
                permissions=[
                    RBAC.permissions.config.create(),
                ],
                role=role_name,
            )

            role = client.roles.by_name(role_name)
            assert role is not None
            assert role.config_permissions is not None
            assert len(role.config_permissions) == 1
            assert role.config_permissions[0].action == RBAC.actions.config.CREATE
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
                permissions=[
                    RBAC.permissions.config.create(),
                    RBAC.permissions.config.delete(),
                ],
            )

            role = client.roles.by_name(role_name)
            assert role is not None
            assert role.config_permissions is not None
            assert len(role.config_permissions) == 2
            assert role.config_permissions[0].action == RBAC.actions.config.CREATE
            assert role.config_permissions[1].action == RBAC.actions.config.DELETE

            client.roles.remove_permissions(
                permissions=[
                    RBAC.permissions.config.delete(),
                ],
                role=role_name,
            )

            role = client.roles.by_name(role_name)
            assert role is not None
            assert role.config_permissions is not None
            assert len(role.config_permissions) == 1
            assert role.config_permissions[0].action == RBAC.actions.config.CREATE

            client.roles.remove_permissions(
                permissions=[
                    RBAC.permissions.config.create(),
                ],
                role=role_name,
            )
            role = client.roles.by_name(role_name)
            assert role is None
        finally:
            client.roles.delete(role_name)


@pytest.fixture
def test_has_permissions_setup(client_factory: ClientFactory) -> Generator[Callable, None, None]:
    created_roles = set()

    def _setup(role_name: str, permissions: List[RBAC.permissions]) -> weaviate.WeaviateClient:
        client = client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS).__enter__()
        if client._connection._weaviate_version.is_lower_than(1, 28, 0):
            pytest.skip("This test requires Weaviate 1.28.0 or higher")
        client.roles.create(name=role_name, permissions=permissions)
        created_roles.add(role_name)
        return client

    yield _setup

    # Cleanup after all tests
    client = client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS)
    try:
        for role_name in created_roles:
            try:
                client.roles.delete(role_name)
            except Exception as e:
                print(f"Warning: Failed to cleanup role {role_name}: {str(e)}")
    finally:
        client.close()


@pytest.mark.parametrize(
    "role_name,permissions,expected",
    [
        # Data permissions test
        (
            "data_role",
            [
                RBAC.permissions.data.read(collection="TestCollection"),
                RBAC.permissions.data.update(collection="TestCollection"),
            ],
            [
                (RBAC.permissions.data.read(collection="TestCollection"), True),
                (RBAC.permissions.data.update(collection="TestCollection"), True),
                (RBAC.permissions.data.delete(collection="TestCollection"), False),
                (RBAC.permissions.data.read(collection="OtherCollection"), False),
            ],
        ),
        # Config permissions test
        (
            "config_role",
            [
                RBAC.permissions.config.update(collection="TestCollection"),
            ],
            [
                (RBAC.permissions.config.update(collection="TestCollection"), True),
                (RBAC.permissions.config.update(collection="OtherCollection"), False),
            ],
        ),
        # Cluster permissions test
        (
            "cluster_role",
            [
                RBAC.permissions.cluster.read(),
            ],
            [
                (RBAC.permissions.cluster.read(), True),
                (RBAC.permissions.config.update(collection="OtherCollection"), False),
            ],
        ),
        # Nodes permissions test
        (
            "nodes_role",
            [
                RBAC.permissions.nodes.read(collection="TestCollection", verbosity="verbose"),
            ],
            [
                (
                    RBAC.permissions.nodes.read(collection="TestCollection", verbosity="verbose"),
                    True,
                ),
                (
                    RBAC.permissions.nodes.read(collection="OtherCollection", verbosity="minimal"),
                    False,
                ),
                (
                    RBAC.permissions.nodes.read(collection="TestCollection", verbosity="minimal"),
                    False,
                ),
            ],
        ),
        # Users permissions test with wildcard
        (
            "users_role",
            [
                RBAC.permissions.users.manage(user="*"),
            ],
            [
                (RBAC.permissions.users.manage(user="*"), True),
                (RBAC.permissions.users.manage(user="specific_user"), False),
            ],
        ),
        # Roles permissions test
        (
            "roles_role",
            [
                RBAC.permissions.roles.manage(role="newrole"),
            ],
            [
                (RBAC.permissions.roles.manage(role="newrole"), True),
                (RBAC.permissions.roles.manage(role="otherrole"), False),
            ],
        ),
        # Backups permissions test
        (
            "backups_role",
            [
                RBAC.permissions.backups.manage(collection="testcollection"),
            ],
            [
                (RBAC.permissions.backups.manage(collection="testcollection"), True),
                (RBAC.permissions.backups.manage(collection="othercollection"), False),
            ],
        ),
        # Multiple permission types test
        (
            "mixed_role",
            [
                RBAC.permissions.data.read(collection="TestCollection"),
                RBAC.permissions.config.update(collection="TestCollection"),
                RBAC.permissions.cluster.read(),
                RBAC.permissions.nodes.read(collection="TestCollection", verbosity="verbose"),
            ],
            [
                (RBAC.permissions.data.read(collection="TestCollection"), True),
                (RBAC.permissions.config.update(collection="TestCollection"), True),
                (RBAC.permissions.cluster.read(), True),
                (
                    RBAC.permissions.nodes.read(collection="TestCollection", verbosity="verbose"),
                    True,
                ),
                (RBAC.permissions.nodes.read(verbosity="verbose"), False),
                (RBAC.permissions.data.update(collection="TestCollection"), False),
                (
                    [
                        RBAC.permissions.data.read(collection="TestCollection"),
                        RBAC.permissions.config.update(collection="TestCollection"),
                        RBAC.permissions.cluster.read(),
                    ],
                    True,
                ),
                (
                    [
                        RBAC.permissions.data.read(collection="TestCollection"),
                        RBAC.permissions.data.delete(collection="TestCollection"),
                    ],
                    False,
                ),
            ],
        ),
    ],
)
def test_has_permissions(
    test_has_permissions_setup: weaviate.WeaviateClient, role_name, permissions, expected
):
    """Test has_permissions with different permission combinations.

    Args:
        client: The Weaviate client
        role_name: Name of the role to create
        permissions: List of permissions to assign to the role
        expected: List of (permission, expected_result) tuples to test
    """
    # Create role with permissions
    client = test_has_permissions_setup(role_name, permissions)
    # Test each permission combination
    for permission, expected_result in expected:
        result = client.roles.has_permissions(
            permissions=permission,
            role=role_name,
        )
        assert result == expected_result, f"Permission check failed for {permission}"
