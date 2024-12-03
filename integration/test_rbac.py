import pytest

from integration.conftest import ClientFactory
from weaviate.auth import Auth
from weaviate.rbac.models import (
    RBAC,
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
            RBAC.permissions.backups.manage(collection="Test"),
            Role(
                name="ManageAllBackups",
                cluster_permissions=None,
                users_permissions=None,
                collections_permissions=None,
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
                cluster_permissions=[ClusterPermission(action=RBAC.actions.cluster.READ)],
                users_permissions=None,
                collections_permissions=None,
                roles_permissions=None,
                data_permissions=None,
                backups_permissions=None,
                nodes_permissions=None,
            ),
        ),
        (
            RBAC.permissions.collections.create(),
            Role(
                name="CreateAllCollections",
                cluster_permissions=None,
                users_permissions=None,
                collections_permissions=[
                    CollectionsPermission(collection="*", action=RBAC.actions.collections.CREATE)
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
                cluster_permissions=None,
                users_permissions=None,
                collections_permissions=None,
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
                cluster_permissions=None,
                users_permissions=None,
                collections_permissions=None,
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
                cluster_permissions=None,
                users_permissions=None,
                collections_permissions=None,
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
                cluster_permissions=None,
                users_permissions=None,
                collections_permissions=None,
                roles_permissions=[RolesPermission(role="*", action=RBAC.actions.roles.MANAGE)],
                data_permissions=None,
                backups_permissions=None,
                nodes_permissions=None,
            ),
        ),
        (
            RBAC.permissions.collections.manage(collection="Test"),
            Role(
                name="ManageTestCollection",
                cluster_permissions=None,
                users_permissions=None,
                collections_permissions=[
                    CollectionsPermission(collection="Test", action=RBAC.actions.collections.MANAGE)
                ],
                roles_permissions=None,
                data_permissions=None,
                backups_permissions=None,
                nodes_permissions=None,
            ),
        ),
        (
            RBAC.permissions.data.manage(collection="Test"),
            Role(
                name="ManageTestData",
                cluster_permissions=None,
                users_permissions=None,
                collections_permissions=None,
                roles_permissions=None,
                data_permissions=[
                    DataPermission(collection="Test", action=RBAC.actions.data.MANAGE)
                ],
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
                    RBAC.permissions.collections.create(),
                ],
            )
            role = client.roles.by_name(role_name)

            assert role is not None
            assert role.collections_permissions is not None
            assert len(role.collections_permissions) == 1
            assert role.collections_permissions[0].action == RBAC.actions.collections.CREATE

            client.roles.add_permissions(
                permissions=[
                    RBAC.permissions.collections.delete(),
                ],
                role=role_name,
            )

            role = client.roles.by_name(role_name)
            assert role is not None
            assert role.collections_permissions is not None
            assert len(role.collections_permissions) == 2
            assert role.collections_permissions[0].action == RBAC.actions.collections.CREATE
            assert role.collections_permissions[1].action == RBAC.actions.collections.DELETE
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
                    RBAC.permissions.collections.create(),
                ],
                role=role_name,
            )

            role = client.roles.by_name(role_name)
            assert role is not None
            assert role.collections_permissions is not None
            assert len(role.collections_permissions) == 1
            assert role.collections_permissions[0].action == RBAC.actions.collections.CREATE
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
                    RBAC.permissions.collections.create(),
                    RBAC.permissions.collections.delete(),
                ],
            )

            role = client.roles.by_name(role_name)
            assert role is not None
            assert role.collections_permissions is not None
            assert len(role.collections_permissions) == 2
            assert role.collections_permissions[0].action == RBAC.actions.collections.CREATE
            assert role.collections_permissions[1].action == RBAC.actions.collections.DELETE

            client.roles.remove_permissions(
                permissions=[
                    RBAC.permissions.collections.delete(),
                ],
                role=role_name,
            )

            role = client.roles.by_name(role_name)
            assert role is not None
            assert role.collections_permissions is not None
            assert len(role.collections_permissions) == 1
            assert role.collections_permissions[0].action == RBAC.actions.collections.CREATE

            client.roles.remove_permissions(
                permissions=[
                    RBAC.permissions.collections.create(),
                ],
                role=role_name,
            )
            role = client.roles.by_name(role_name)
            assert role is None
        finally:
            client.roles.delete(role_name)
