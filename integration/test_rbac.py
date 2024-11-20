import pytest

from integration.conftest import ClientFactory
from weaviate.auth import Auth
from weaviate.rbac.models import (
    RBAC,
    Role,
    CollectionsPermission,
    RolesPermission,
    TenantsPermission,
)


RBAC_PORTS = (8092, 50063)
RBAC_AUTH_CREDS = Auth.api_key("existing-key")


@pytest.mark.parametrize(
    "permissions,expected",
    [
        (
            RBAC.permissions.collections.create(),
            Role(
                name="CreateAllCollections",
                cluster_actions=None,
                users_permissions=None,
                collections_permissions=[
                    CollectionsPermission(collection="*", action=RBAC.actions.collection.CREATE)
                ],
                roles_permissions=None,
                tenants_permissions=None,
                objects_collection_permissions=None,
                objects_tenant_permissions=None,
            ),
        ),
        (
            RBAC.permissions.roles.manage(),
            Role(
                name="ManageAllRoles",
                cluster_actions=None,
                users_permissions=None,
                collections_permissions=None,
                roles_permissions=[RolesPermission(role="*", action=RBAC.actions.roles.MANAGE)],
                tenants_permissions=None,
                objects_collection_permissions=None,
                objects_tenant_permissions=None,
            ),
        ),
        (
            RBAC.permissions.tenants.read(collection="foo"),
            Role(
                name="ReadAllTenantsInFoo",
                cluster_actions=None,
                users_permissions=None,
                collections_permissions=None,
                roles_permissions=None,
                tenants_permissions=[
                    TenantsPermission(
                        collection="foo", tenant="*", action=RBAC.actions.tenants.READ
                    )
                ],
                objects_collection_permissions=None,
                objects_tenant_permissions=None,
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
        role_name = "ExistingRole"
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
            assert role.collections_permissions[0].action == RBAC.actions.collection.CREATE

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
            assert role.collections_permissions[0].action == RBAC.actions.collection.CREATE
            assert role.collections_permissions[1].action == RBAC.actions.collection.DELETE
        finally:
            client.roles.delete(role_name)


def test_upsert_permissions(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 28, 0):
            pytest.skip("This test requires Weaviate 1.28.0 or higher")
        role_name = "ExistingRole"
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
            assert role.collections_permissions[0].action == RBAC.actions.collection.CREATE
        finally:
            client.roles.delete(role_name)


def test_downsert_permissions(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 28, 0):
            pytest.skip("This test requires Weaviate 1.28.0 or higher")
        role_name = "ExistingRole"
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
            assert role.collections_permissions[0].action == RBAC.actions.collection.CREATE
            assert role.collections_permissions[1].action == RBAC.actions.collection.DELETE

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
            assert role.collections_permissions[0].action == RBAC.actions.collection.CREATE

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
