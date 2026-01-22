from typing import List, Optional

import pytest
from _pytest.fixtures import SubRequest

from integration.conftest import ClientFactory, _sanitize_collection_name
from weaviate.auth import Auth
from weaviate.classes.rbac import Actions, Permissions, RoleScope
from weaviate.connect.helpers import connect_to_local
from weaviate.rbac.models import (
    AliasPermissionOutput,
    BackupsPermissionOutput,
    ClusterPermissionOutput,
    CollectionsPermissionOutput,
    DataPermissionOutput,
    GroupsPermissionOutput,
    NodesPermissionOutput,
    Role,
    ReplicatePermissionOutput,
    RolesPermissionOutput,
    TenantsPermissionOutput,
    UsersPermissionOutput,
    UserTypes,
    _Permission,
)

RBAC_PORTS = (8092, 50063)
RBAC_AUTH_CREDS = Auth.api_key("admin-key")


@pytest.mark.parametrize(
    "permissions,expected,min_version",
    [
        (
            Permissions.backup(collection="Test", manage=True),
            Role(
                name="ManageAllBackups",
                alias_permissions=[],
                cluster_permissions=[],
                users_permissions=[],
                collections_permissions=[],
                roles_permissions=[],
                data_permissions=[],
                backups_permissions=[
                    BackupsPermissionOutput(collection="Test", actions={Actions.Backups.MANAGE})
                ],
                nodes_permissions=[],
                tenants_permissions=[],
                replicate_permissions=[],
                groups_permissions=[],
            ),
            None,
        ),
        (
            Permissions.cluster(read=True),
            Role(
                name="ReadCluster",
                alias_permissions=[],
                cluster_permissions=[ClusterPermissionOutput(actions={Actions.Cluster.READ})],
                users_permissions=[],
                collections_permissions=[],
                roles_permissions=[],
                data_permissions=[],
                backups_permissions=[],
                nodes_permissions=[],
                tenants_permissions=[],
                replicate_permissions=[],
                groups_permissions=[],
            ),
            None,
        ),
        (
            Permissions.collections(collection="Test", create_collection=True),
            Role(
                name="CreateAllCollections",
                alias_permissions=[],
                cluster_permissions=[],
                users_permissions=[],
                collections_permissions=[
                    CollectionsPermissionOutput(
                        collection="Test", actions={Actions.Collections.CREATE}
                    )
                ],
                roles_permissions=[],
                data_permissions=[],
                backups_permissions=[],
                nodes_permissions=[],
                tenants_permissions=[],
                replicate_permissions=[],
                groups_permissions=[],
            ),
            None,
        ),
        (
            Permissions.data(collection="*", create=True),
            Role(
                name="CreateAllData",
                alias_permissions=[],
                cluster_permissions=[],
                users_permissions=[],
                collections_permissions=[],
                roles_permissions=[],
                data_permissions=[
                    DataPermissionOutput(collection="*", tenant="*", actions={Actions.Data.CREATE})
                ],
                backups_permissions=[],
                nodes_permissions=[],
                tenants_permissions=[],
                replicate_permissions=[],
                groups_permissions=[],
            ),
            None,
        ),
        (
            Permissions.data(
                collection=["ColA", "ColB"], tenant=["tenant1", "tenant2"], create=True
            ),
            Role(
                name="CreateDataInColsAndTenants",
                alias_permissions=[],
                cluster_permissions=[],
                users_permissions=[],
                collections_permissions=[],
                roles_permissions=[],
                data_permissions=[
                    DataPermissionOutput(
                        collection="ColA", tenant="tenant1", actions={Actions.Data.CREATE}
                    ),
                    DataPermissionOutput(
                        collection="ColA", tenant="tenant2", actions={Actions.Data.CREATE}
                    ),
                    DataPermissionOutput(
                        collection="ColB", tenant="tenant1", actions={Actions.Data.CREATE}
                    ),
                    DataPermissionOutput(
                        collection="ColB", tenant="tenant2", actions={Actions.Data.CREATE}
                    ),
                ],
                backups_permissions=[],
                nodes_permissions=[],
                tenants_permissions=[],
                replicate_permissions=[],
                groups_permissions=[],
            ),
            None,
        ),
        (
            Permissions.Nodes.verbose(collection="Test", read=True),
            Role(
                name="VerboseNodes",
                alias_permissions=[],
                cluster_permissions=[],
                users_permissions=[],
                collections_permissions=[],
                roles_permissions=[],
                data_permissions=[],
                backups_permissions=[],
                nodes_permissions=[
                    NodesPermissionOutput(
                        verbosity="verbose", actions={Actions.Nodes.READ}, collection="Test"
                    )
                ],
                tenants_permissions=[],
                replicate_permissions=[],
                groups_permissions=[],
            ),
            None,
        ),
        (
            Permissions.Nodes.minimal(read=True),
            Role(
                name="MinimalNodes",
                alias_permissions=[],
                cluster_permissions=[],
                users_permissions=[],
                collections_permissions=[],
                roles_permissions=[],
                data_permissions=[],
                backups_permissions=[],
                nodes_permissions=[
                    NodesPermissionOutput(
                        verbosity="minimal", actions={Actions.Nodes.READ}, collection="*"
                    )
                ],
                tenants_permissions=[],
                replicate_permissions=[],
                groups_permissions=[],
            ),
            None,
        ),
        (
            Permissions.roles(role="*", create=True),
            Role(
                name="ManageAllRoles",
                alias_permissions=[],
                cluster_permissions=[],
                users_permissions=[],
                collections_permissions=[],
                roles_permissions=[
                    RolesPermissionOutput(
                        role="*", actions={Actions.Roles.CREATE}, scope=RoleScope.MATCH
                    )
                ],
                data_permissions=[],
                backups_permissions=[],
                nodes_permissions=[],
                tenants_permissions=[],
                replicate_permissions=[],
                groups_permissions=[],
            ),
            None,
        ),
        (
            Permissions.tenants(collection="*", read=True, update=True),
            Role(
                name="TenantsReadRole",
                alias_permissions=[],
                cluster_permissions=[],
                users_permissions=[],
                collections_permissions=[],
                roles_permissions=[],
                data_permissions=[],
                backups_permissions=[],
                nodes_permissions=[],
                tenants_permissions=[
                    TenantsPermissionOutput(
                        collection="*",
                        tenant="*",
                        actions={Actions.Tenants.READ, Actions.Tenants.UPDATE},
                    )
                ],
                replicate_permissions=[],
                groups_permissions=[],
            ),
            None,
        ),
        (
            Permissions.tenants(
                collection=["ColA", "ColB"], tenant=["tenant1", "tenant2"], read=True, update=True
            ),
            Role(
                name="ReadSpecificTenantsInCols",
                cluster_permissions=[],
                alias_permissions=[],
                users_permissions=[],
                collections_permissions=[],
                roles_permissions=[],
                data_permissions=[],
                backups_permissions=[],
                nodes_permissions=[],
                tenants_permissions=[
                    TenantsPermissionOutput(
                        collection="ColA",
                        tenant="tenant1",
                        actions={Actions.Tenants.READ, Actions.Tenants.UPDATE},
                    ),
                    TenantsPermissionOutput(
                        collection="ColA",
                        tenant="tenant2",
                        actions={Actions.Tenants.READ, Actions.Tenants.UPDATE},
                    ),
                    TenantsPermissionOutput(
                        collection="ColB",
                        tenant="tenant1",
                        actions={Actions.Tenants.READ, Actions.Tenants.UPDATE},
                    ),
                    TenantsPermissionOutput(
                        collection="ColB",
                        tenant="tenant2",
                        actions={Actions.Tenants.READ, Actions.Tenants.UPDATE},
                    ),
                ],
                replicate_permissions=[],
                groups_permissions=[],
            ),
            None,
        ),
        (
            Permissions.users(user="*", assign_and_revoke=True, read=True),
            Role(
                name="UserAssignRole",
                cluster_permissions=[],
                alias_permissions=[],
                users_permissions=[
                    UsersPermissionOutput(
                        users="*", actions={Actions.Users.ASSIGN_AND_REVOKE, Actions.Users.READ}
                    )
                ],
                collections_permissions=[],
                roles_permissions=[],
                data_permissions=[],
                backups_permissions=[],
                nodes_permissions=[],
                tenants_permissions=[],
                replicate_permissions=[],
                groups_permissions=[],
            ),
            None,
        ),
        (
            Permissions.replicate(
                collection=["ColA", "ColB"], shard=["tenant1", "tenant2"], read=True, update=True
            ),
            Role(
                name="Replicate",
                cluster_permissions=[],
                alias_permissions=[],
                users_permissions=[],
                collections_permissions=[],
                roles_permissions=[],
                data_permissions=[],
                backups_permissions=[],
                nodes_permissions=[],
                tenants_permissions=[],
                replicate_permissions=[
                    ReplicatePermissionOutput(
                        collection="ColA",
                        shard="tenant1",
                        actions={Actions.Replicate.READ, Actions.Replicate.UPDATE},
                    ),
                    ReplicatePermissionOutput(
                        collection="ColA",
                        shard="tenant2",
                        actions={Actions.Replicate.READ, Actions.Replicate.UPDATE},
                    ),
                    ReplicatePermissionOutput(
                        collection="ColB",
                        shard="tenant1",
                        actions={Actions.Replicate.READ, Actions.Replicate.UPDATE},
                    ),
                    ReplicatePermissionOutput(
                        collection="ColB",
                        shard="tenant2",
                        actions={Actions.Replicate.READ, Actions.Replicate.UPDATE},
                    ),
                ],
                groups_permissions=[],
            ),
            32,
        ),
        (
            Permissions.alias(alias="", collection="*", read=True, delete=True),
            Role(
                name="AlliasRole2",
                alias_permissions=[
                    AliasPermissionOutput(
                        alias="*",
                        collection="*",
                        actions={Actions.Alias.READ, Actions.Alias.DELETE},
                    )
                ],
                cluster_permissions=[],
                users_permissions=[],
                collections_permissions=[],
                roles_permissions=[],
                data_permissions=[],
                backups_permissions=[],
                nodes_permissions=[],
                tenants_permissions=[],
                replicate_permissions=[],
                groups_permissions=[],
            ),
            32,  # Minimum version for alias permissions
        ),
        (
            Permissions.alias(alias="*", collection="*", read=True, delete=True),
            Role(
                name="AlliasRole",
                alias_permissions=[
                    AliasPermissionOutput(
                        alias="*",
                        collection="*",
                        actions={Actions.Alias.READ, Actions.Alias.DELETE},
                    )
                ],
                cluster_permissions=[],
                users_permissions=[],
                collections_permissions=[],
                roles_permissions=[],
                data_permissions=[],
                backups_permissions=[],
                nodes_permissions=[],
                tenants_permissions=[],
                replicate_permissions=[],
                groups_permissions=[],
            ),
            32,  # Minimum version for alias permissions
        ),
        (
            Permissions.alias(alias="myCAR", collection="*", read=True, delete=True),
            Role(
                name="AlliasRole",
                alias_permissions=[
                    AliasPermissionOutput(
                        alias="MyCAR",  # capitalized the first letter.
                        collection="*",
                        actions={Actions.Alias.READ, Actions.Alias.DELETE},
                    )
                ],
                cluster_permissions=[],
                users_permissions=[],
                collections_permissions=[],
                roles_permissions=[],
                data_permissions=[],
                backups_permissions=[],
                nodes_permissions=[],
                tenants_permissions=[],
                replicate_permissions=[],
                groups_permissions=[],
            ),
            32,  # Minimum version for alias permissions
        ),
        (
            Permissions.Groups.oidc(group="MyGroup", read=True),
            Role(
                name="GroupRole",
                alias_permissions=[],
                cluster_permissions=[],
                users_permissions=[],
                collections_permissions=[],
                roles_permissions=[],
                data_permissions=[],
                backups_permissions=[],
                nodes_permissions=[],
                tenants_permissions=[],
                replicate_permissions=[],
                groups_permissions=[
                    GroupsPermissionOutput(
                        group="MyGroup",
                        group_type="oidc",
                        actions={Actions.Groups.READ},
                    )
                ],
            ),
            32,  # Minimum version for group permissions
        ),
    ],
)
def test_create_role(
    client_factory: ClientFactory,
    permissions: List[_Permission],
    expected: Role,
    min_version: Optional[int],
) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 28, 0):
            pytest.skip("This test requires Weaviate 1.28.0 or higher")
        if min_version is not None and client._connection._weaviate_version.is_lower_than(
            1, min_version, 0
        ):
            pytest.skip(f"This test requires Weaviate 1.{min_version}.0 or higher")

        try:
            client.roles.delete(expected.name)
            client.roles.create(
                role_name=expected.name,
                permissions=permissions,
            )
            role = client.roles.get(expected.name)
            assert role is not None
            assert role == expected
        finally:
            client.roles.delete(expected.name)


def test_add_permissions_to_existing(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 28, 0):
            pytest.skip("This test requires Weaviate 1.28.0 or higher")
        role_name = "ExistingRolePermissionsAdd"
        client.roles.delete(role_name)
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
            assert role.collections_permissions[0].actions == {Actions.Collections.CREATE}

            client.roles.add_permissions(
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
            assert role.collections_permissions[0].actions == {
                Actions.Collections.CREATE,
                Actions.Collections.DELETE,
            }
        finally:
            client.roles.delete(role_name)


def test_remove_permissions_from_existing(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 28, 0):
            pytest.skip("This test requires Weaviate 1.28.0 or higher")
        role_name = "ExistingRolePermissionsRemove"
        client.roles.delete(role_name)
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
            assert len(role.collections_permissions) == 1
            assert len(role.collections_permissions[0].actions) == 2
            assert len(role.permissions) == 1

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
            assert role.collections_permissions[0].actions == {Actions.Collections.CREATE}
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
            assert len(role.permissions) == 2
            assert role.collections_permissions is not None
            assert len(role.collections_permissions) == 1
            assert role.collections_permissions[0].actions == {Actions.Collections.READ}
            assert len(role.data_permissions) == 1
            assert role.data_permissions[0].actions == {Actions.Data.CREATE, Actions.Data.UPDATE}

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
def test_role_scope(client_factory: ClientFactory, scope: RoleScope, request: SubRequest) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 28, 4):
            pytest.skip("This test requires Weaviate 1.28.4 or higher")
        role_name = _sanitize_collection_name(request.node.name) + "_scope"
        try:
            client.roles.delete(role_name)
            client.roles.create(
                role_name=role_name,
                permissions=Permissions.roles(role="test", scope=scope, read=True),
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
        client.users.assign_roles(user_id="admin-user", role_names="viewer")
        assigned_users = client.roles.get_assigned_user_ids("viewer")
        assert len(assigned_users) == 1
        assert assigned_users[0] == "admin-user"


def test_get_assigned_users_db(client_factory: ClientFactory, request: SubRequest) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 30, 0):
            pytest.skip("This test requires Weaviate 1.30.0 or higher")

        names = _sanitize_collection_name(request.node.name)
        client.roles.delete(names)
        client.roles.create(
            role_name=names,
            permissions=Permissions.roles(role="test", read=True),
        )

        client.users.db.create(user_id=names)

        client.users.db.assign_roles(user_id=names, role_names=names)
        assigned_users = client.roles.get_user_assignments(names)
        assert len(assigned_users) == 1
        assert assigned_users[0].user_id == names
        assert assigned_users[0].user_type == UserTypes.DB_DYNAMIC

        client.roles.delete(names)
        client.users.db.delete(user_id=names)


def test_get_assigned_oidc_db(client_factory: ClientFactory, request: SubRequest) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 30, 0):
            pytest.skip("This test requires Weaviate 1.30.0 or higher")

        names = _sanitize_collection_name(request.node.name)
        client.roles.delete(names)
        client.roles.create(
            role_name=names,
            permissions=Permissions.roles(role="test", read=True),
        )

        client.users.oidc.assign_roles(user_id=names, role_names=names)
        assigned_users = client.roles.get_user_assignments(names)
        assert len(assigned_users) == 1
        assert assigned_users[0].user_id == names
        assert assigned_users[0].user_type == UserTypes.OIDC

        client.roles.delete(names)


def test_permission_output_as_input(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 28, 0):
            pytest.skip("This test requires Weaviate 1.28.0 or higher")
        role_name = "PermissionOutputAsInput"
        try:
            client.roles.create(
                role_name=role_name,
                permissions=Permissions.roles(role="test", read=True),
            )
            role = client.roles.get(role_name)
            assert role is not None
            assert len(role.permissions) == 1

            client.roles.create(
                role_name=role_name + "2",
                permissions=role.permissions,
            )

            role2 = client.roles.get(role_name)
            assert role2 is not None
            assert len(role2.permissions) == 1
            assert role2.permissions == role.permissions

        finally:
            client.roles.delete(role_name)
            client.roles.delete(role_name=role_name + "2")


def test_permission_joining(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 28, 0):
            pytest.skip("This test requires Weaviate 1.28.0 or higher")
        role_name = "PermissionJoining"
        try:
            client.roles.create(
                role_name=role_name,
                permissions=[
                    Permissions.collections(
                        collection="test", read_config=True, update_config=True
                    ),
                    Permissions.collections(
                        collection="test", create_collection=True, update_config=True
                    ),
                    Permissions.collections(
                        collection="test*", read_config=True, update_config=True
                    ),
                    Permissions.collections(
                        collection="test*", create_collection=True, update_config=True
                    ),
                    Permissions.collections(
                        collection="test_*", read_config=True, update_config=True
                    ),
                    Permissions.collections(
                        collection="test_*", create_collection=True, update_config=True
                    ),
                ],
            )
            role = client.roles.get(role_name)
            assert role is not None
            assert len(role.permissions) == 3
            assert len(role.collections_permissions) == 3
            assert role.collections_permissions[0].actions == {
                Actions.Collections.READ,
                Actions.Collections.CREATE,
                Actions.Collections.UPDATE,
            }
            assert role.collections_permissions[1].actions == {
                Actions.Collections.READ,
                Actions.Collections.CREATE,
                Actions.Collections.UPDATE,
            }
            assert role.collections_permissions[2].actions == {
                Actions.Collections.READ,
                Actions.Collections.CREATE,
                Actions.Collections.UPDATE,
            }

        finally:
            client.roles.delete(role_name)


def test_server_side_batching_with_auth() -> None:
    collection_name = "TestSSBAuth"
    with connect_to_local(
        port=RBAC_PORTS[0], grpc_port=RBAC_PORTS[1], auth_credentials=RBAC_AUTH_CREDS
    ) as client:
        if client._connection._weaviate_version.is_lower_than(1, 34, 0):
            pytest.skip("Server-side batching not supported in Weaviate < 1.34.0")
        collection = client.collections.create(collection_name)
        with client.batch.experimental() as batch:
            batch.add_object(collection_name)
            batch.add_object(collection_name)
            batch.add_object(collection_name)
        try:
            assert len(collection) == 3
        finally:
            client.collections.delete(collection_name)
