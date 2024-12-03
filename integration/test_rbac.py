import pytest

from integration.conftest import ClientFactory
from weaviate.auth import Auth
from weaviate.rbac.models import (
    Role,
    Permissions,
    ClusterPermission,
    CollectionsPermission,
    DataPermission,
    RolesPermission,
    BackupsPermission,
    NodesPermission,
    BackupsAction,
    ClusterAction,
    CollectionsAction,
    DataAction,
    NodesAction,
    RolesAction,
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
                cluster_permissions=None,
                users_permissions=None,
                collections_permissions=None,
                roles_permissions=None,
                data_permissions=None,
                backups_permissions=[
                    BackupsPermission(collection="Test", action=BackupsAction.MANAGE)
                ],
                nodes_permissions=None,
            ),
        ),
        (
            Permissions.cluster(read=True),
            Role(
                name="ReadCluster",
                cluster_permissions=[ClusterPermission(action=ClusterAction.READ)],
                users_permissions=None,
                collections_permissions=None,
                roles_permissions=None,
                data_permissions=None,
                backups_permissions=None,
                nodes_permissions=None,
            ),
        ),
        (
            Permissions.collection_config(collection="Test", create_collection=True),
            Role(
                name="CreateAllCollections",
                cluster_permissions=None,
                users_permissions=None,
                collections_permissions=[
                    CollectionsPermission(collection="Test", action=CollectionsAction.CREATE)
                ],
                roles_permissions=None,
                data_permissions=None,
                backups_permissions=None,
                nodes_permissions=None,
            ),
        ),
        (
            Permissions.data(collection="*", create=True),
            Role(
                name="CreateAllData",
                cluster_permissions=None,
                users_permissions=None,
                collections_permissions=None,
                roles_permissions=None,
                data_permissions=[DataPermission(collection="*", action=DataAction.CREATE)],
                backups_permissions=None,
                nodes_permissions=None,
            ),
        ),
        (
            Permissions.nodes(collection="test", read=True, verbosity="minimal"),
            Role(
                name="MinimalNodes",
                cluster_permissions=None,
                users_permissions=None,
                collections_permissions=None,
                roles_permissions=None,
                data_permissions=None,
                backups_permissions=None,
                nodes_permissions=[
                    NodesPermission(verbosity="minimal", action=NodesAction.READ, collection=None)
                ],
            ),
        ),
        (
            Permissions.nodes(verbosity="verbose", collection="Test", read=True),
            Role(
                name="VerboseNodes",
                cluster_permissions=None,
                users_permissions=None,
                collections_permissions=None,
                roles_permissions=None,
                data_permissions=None,
                backups_permissions=None,
                nodes_permissions=[
                    NodesPermission(verbosity="verbose", action=NodesAction.READ, collection="Test")
                ],
            ),
        ),
        (
            Permissions.roles(role="*", manage=True),
            Role(
                name="ManageAllRoles",
                cluster_permissions=None,
                users_permissions=None,
                collections_permissions=None,
                roles_permissions=[RolesPermission(role="*", action=RolesAction.MANAGE)],
                data_permissions=None,
                backups_permissions=None,
                nodes_permissions=None,
            ),
        ),
        (
            Permissions.collection_config(collection="Test", manage_collection=True),
            Role(
                name="ManageTestCollection",
                cluster_permissions=None,
                users_permissions=None,
                collections_permissions=[
                    CollectionsPermission(collection="Test", action=CollectionsAction.MANAGE)
                ],
                roles_permissions=None,
                data_permissions=None,
                backups_permissions=None,
                nodes_permissions=None,
            ),
        ),
        (
            Permissions.data(collection="Test", manage=True),
            Role(
                name="ManageTestData",
                cluster_permissions=None,
                users_permissions=None,
                collections_permissions=None,
                roles_permissions=None,
                data_permissions=[DataPermission(collection="Test", action=DataAction.MANAGE)],
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
                permissions=Permissions.collection_config(collection="*", create_collection=True),
            )
            role = client.roles.by_name(role_name)

            assert role is not None
            assert role.collections_permissions is not None
            assert len(role.collections_permissions) == 1
            assert role.collections_permissions[0].action == CollectionsAction.CREATE

            client.roles.add_permissions(
                permissions=[
                    Permissions.collection_config(collection="*", delete_collection=True),
                ],
                role=role_name,
            )

            role = client.roles.by_name(role_name)
            assert role is not None
            assert role.collections_permissions is not None
            assert len(role.collections_permissions) == 2
            assert role.collections_permissions[0].action == CollectionsAction.CREATE
            assert role.collections_permissions[1].action == CollectionsAction.DELETE
        finally:
            client.roles.delete(role_name)


def test_upsert_permissions(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 28, 0):
            pytest.skip("This test requires Weaviate 1.28.0 or higher")
        role_name = "ExistingRoleUpsert"
        try:
            client.roles.add_permissions(
                permissions=Permissions.collection_config(collection="*", create_collection=True),
                role=role_name,
            )

            role = client.roles.by_name(role_name)
            assert role is not None
            assert role.collections_permissions is not None
            assert len(role.collections_permissions) == 1
            assert role.collections_permissions[0].action == CollectionsAction.CREATE
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
                permissions=Permissions.collection_config(
                    collection="*", create_collection=True, delete_collection=True
                ),
            )

            role = client.roles.by_name(role_name)
            assert role is not None
            assert role.collections_permissions is not None
            assert len(role.collections_permissions) == 2
            assert role.collections_permissions[0].action == CollectionsAction.CREATE
            assert role.collections_permissions[1].action == CollectionsAction.DELETE

            client.roles.remove_permissions(
                permissions=Permissions.collection_config(collection="*", delete_collection=True),
                role=role_name,
            )

            role = client.roles.by_name(role_name)
            assert role is not None
            assert role.collections_permissions is not None
            assert len(role.collections_permissions) == 1
            assert role.collections_permissions[0].action == CollectionsAction.CREATE

            client.roles.remove_permissions(
                permissions=Permissions.collection_config(collection="*", create_collection=True),
                role=role_name,
            )
            role = client.roles.by_name(role_name)
            assert role is None
        finally:
            client.roles.delete(role_name)
