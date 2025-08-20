import random

import pytest

import weaviate
from integration.conftest import ClientFactory
from weaviate.auth import Auth
from weaviate.rbac.models import Role, RoleBase, UserTypes

RBAC_PORTS = (8092, 50063)
RBAC_AUTH_CREDS = Auth.api_key("admin-key")


def test_own_user(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 28, 0):
            pytest.skip("This test requires Weaviate 1.28.0 or higher")
        user = client.users.get_my_user()
        assert len(user.roles) > 0
        assert user.user_id == "admin-user"


def test_get_user_roles_deprecated(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 28, 0):
            pytest.skip("This test requires Weaviate 1.28.0 or higher")
        roles = client.users.get_assigned_roles("admin-user")
        assert len(roles) > 0


def test_get_user_roles_db(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 30, 0):
            pytest.skip("This test requires Weaviate 1.30.0 or higher")
        roles_base = client.users.db.get_assigned_roles(user_id="admin-user")
        names = list(roles_base.keys())
        assert len(roles_base) > 0
        assert isinstance(roles_base[names[0]], RoleBase)

        roles = client.users.db.get_assigned_roles(user_id="admin-user", include_permissions=True)
        assert len(roles) > 0
        assert isinstance(roles[names[0]], Role)


def test_get_user_roles_oidc(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 30, 0):
            pytest.skip("This test requires Weaviate 1.30.0 or higher")
        roles_base = client.users.oidc.get_assigned_roles(user_id="admin-user")
        names = list(roles_base.keys())
        assert len(roles_base) > 0
        assert isinstance(roles_base[names[0]], RoleBase)

        roles = client.users.oidc.get_assigned_roles(user_id="admin-user", include_permissions=True)
        assert len(roles) > 0
        assert isinstance(roles[names[0]], Role)


def test_get_user_with_no_roles(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=Auth.api_key("custom-key")) as client:
        if client._connection._weaviate_version.is_lower_than(1, 28, 0):
            pytest.skip("This test requires Weaviate 1.28.0 or higher")
        user = client.users.get_my_user()
        assert len(user.roles) == 0


def test_get_static_db_user(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 30, 0):
            pytest.skip("This test requires Weaviate 1.30.0 or higher")
        user = client.users.db.get(user_id="admin-user")
        assert len(user.role_names) > 0
        assert user.user_id == "admin-user"
        assert user.active
        assert user.user_type == UserTypes.DB_STATIC


def test_create_user_and_get(client_factory: ClientFactory) -> None:
    with client_factory(ports=(RBAC_PORTS), auth_credentials=Auth.api_key("admin-key")) as client:
        if client._connection._weaviate_version.is_lower_than(1, 30, 0):
            pytest.skip("This test requires Weaviate 1.30.0 or higher")

        randomUserName = "new-user" + str(random.randint(1, 1000))
        apiKey = client.users.db.create(user_id=randomUserName)
        with weaviate.connect_to_local(
            port=RBAC_PORTS[0], grpc_port=RBAC_PORTS[1], auth_credentials=Auth.api_key(apiKey)
        ) as client2:
            user = client2.users.get_my_user()
            assert user.user_id == randomUserName
        dynamicUser = client.users.db.get(user_id=randomUserName)
        assert dynamicUser is not None
        assert dynamicUser.user_id == randomUserName
        assert dynamicUser.user_type == UserTypes.DB_DYNAMIC
        assert client.users.db.delete(user_id=randomUserName)


def test_delete_user(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=Auth.api_key("admin-key")) as client:
        if client._connection._weaviate_version.is_lower_than(1, 30, 0):
            pytest.skip("This test requires Weaviate 1.30.0 or higher")

        randomUserName = "new-user" + str(random.randint(1, 1000))
        client.users.db.create(user_id=randomUserName)
        assert client.users.db.delete(user_id=randomUserName)

        assert not client.users.db.delete(user_id="I-do-not-exist")


def test_rotate_user_key(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=Auth.api_key("admin-key")) as client:
        if client._connection._weaviate_version.is_lower_than(1, 30, 0):
            pytest.skip("This test requires Weaviate 1.30.0 or higher")

        randomUserName = "new-user" + str(random.randint(1, 1000))
        apiKey = client.users.db.create(user_id=randomUserName)
        with weaviate.connect_to_local(
            port=RBAC_PORTS[0], grpc_port=RBAC_PORTS[1], auth_credentials=Auth.api_key(apiKey)
        ) as client2:
            user = client2.users.get_my_user()
            assert user.user_id == randomUserName

        apiKeyNew = client.users.db.rotate_key(user_id=randomUserName)
        with weaviate.connect_to_local(
            port=RBAC_PORTS[0], grpc_port=RBAC_PORTS[1], auth_credentials=Auth.api_key(apiKeyNew)
        ) as client2:
            user = client2.users.get_my_user()
            assert user.user_id == randomUserName

        assert client.users.db.delete(user_id=randomUserName)


def test_de_activate(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=Auth.api_key("admin-key")) as client:
        if client._connection._weaviate_version.is_lower_than(1, 30, 0):
            pytest.skip("This test requires Weaviate 1.30.0 or higher")

        randomUserName = "new-user" + str(random.randint(1, 1000))
        client.users.db.create(user_id=randomUserName)

        assert client.users.db.deactivate(user_id=randomUserName)
        assert not client.users.db.deactivate(
            user_id=randomUserName
        )  # second deactivation returns a conflict => false
        user = client.users.db.get(user_id=randomUserName)
        assert not user.active
        assert client.users.db.activate(user_id=randomUserName)
        assert not client.users.db.activate(
            user_id=randomUserName
        )  # second activation returns a conflict => false
        user = client.users.db.get(user_id=randomUserName)
        assert user.active

        client.users.db.delete(user_id=randomUserName)


def test_deactivate_and_revoke(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=Auth.api_key("admin-key")) as client:
        if client._connection._weaviate_version.is_lower_than(1, 30, 0):
            pytest.skip("This test requires Weaviate 1.30.0 or higher")

        randomUserName = "new-user" + str(random.randint(1, 1000))
        apiKeyOld = client.users.db.create(user_id=randomUserName)
        assert client.users.db.deactivate(user_id=randomUserName, revoke_key=True)

        with pytest.raises(weaviate.exceptions.UnexpectedStatusCodeError):
            weaviate.connect_to_local(
                port=RBAC_PORTS[0],
                grpc_port=RBAC_PORTS[1],
                auth_credentials=Auth.api_key(apiKeyOld),
            )

        # re-activating is not enough
        assert client.users.db.activate(user_id=randomUserName)
        with pytest.raises(weaviate.exceptions.UnexpectedStatusCodeError):
            weaviate.connect_to_local(
                port=RBAC_PORTS[0],
                grpc_port=RBAC_PORTS[1],
                auth_credentials=Auth.api_key(apiKeyOld),
            )

        apiKeyNew = client.users.db.rotate_key(user_id=randomUserName)

        with weaviate.connect_to_local(
            port=RBAC_PORTS[0], grpc_port=RBAC_PORTS[1], auth_credentials=Auth.api_key(apiKeyNew)
        ) as client2:
            user = client2.users.get_my_user()
            assert user.user_id == randomUserName

        client.users.db.delete(user_id=randomUserName)


def test_deprecated_syntax(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=Auth.api_key("admin-key")) as client:
        if client._connection._weaviate_version.is_lower_than(1, 30, 0):
            pytest.skip("This test requires Weaviate 1.30.0 or higher")
        randomUserName = "new-user" + str(random.randint(1, 1000))
        client.users.db.create(user_id=randomUserName)
        roles = client.users.db.get_assigned_roles(user_id=randomUserName)
        assert len(roles) == 0
        client.users.db.delete(user_id=randomUserName)


def test_list_all_users(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=Auth.api_key("admin-key")) as client:
        if client._connection._weaviate_version.is_lower_than(1, 30, 0):
            pytest.skip("This test requires Weaviate 1.30.0 or higher")

        for i in range(5):
            client.users.db.delete(user_id=f"list-all-user-{i}")
            client.users.db.create(user_id=f"list-all-user-{i}")

        users = client.users.db.list_all()
        dynamic_users = [user for user in users if user.user_id.startswith("list-all-")]
        assert len(dynamic_users) == 5
        for i in range(5):
            client.users.db.delete(user_id=f"list-all-{i}")
