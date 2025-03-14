import random
import pytest

from integration.conftest import ClientFactory
from weaviate.auth import Auth

import weaviate


RBAC_PORTS = (8092, 50063)
RBAC_AUTH_CREDS = Auth.api_key("admin-key")


def test_own_user(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 28, 0):
            pytest.skip("This test requires Weaviate 1.28.0 or higher")
        user = client.users.get_my_user()
        assert len(user.roles) > 0
        assert user.user_id == "admin-user"


def test_get_users(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=RBAC_AUTH_CREDS) as client:
        if client._connection._weaviate_version.is_lower_than(1, 28, 0):
            pytest.skip("This test requires Weaviate 1.28.0 or higher")
        roles = client.users.get_assigned_roles("admin-user")
        assert len(roles) > 0


def test_get_user_with_no_roles(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=Auth.api_key("custom-key")) as client:
        if client._connection._weaviate_version.is_lower_than(1, 28, 0):
            pytest.skip("This test requires Weaviate 1.28.0 or higher")
        user = client.users.get_my_user()
        assert len(user.roles) == 0


def test_create_user_and_get(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=Auth.api_key("admin-key")) as client:
        if client._connection._weaviate_version.is_lower_than(1, 30, 0):
            pytest.skip("This test requires Weaviate 1.30.0 or higher")

        randomUserName = "new-user" + str(random.randint(1, 1000))
        apiKey = client.users.db.create(user_id=randomUserName)
        with weaviate.connect_to_local(
            port=8081, grpc_port=50052, auth_credentials=Auth.api_key(apiKey)
        ) as client2:
            user = client2.users.get_my_user()
            assert user.user_id == randomUserName
        user = client.users.db.get(user_id=randomUserName)
        assert user.user_id == randomUserName
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
            port=8081, grpc_port=50052, auth_credentials=Auth.api_key(apiKey)
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

        client.users.db.deactivate(user_id=randomUserName)
        user = client.users.db.get(user_id=randomUserName)
        user.roles
        assert not user.active
        client.users.db.activate(user_id=randomUserName)
        user = client.users.db.get(user_id=randomUserName)
        assert user.active

        client.users.db.delete(user_id=randomUserName)


def test_deprecated_syntax(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=Auth.api_key("admin-key")) as client:
        if client._connection._weaviate_version.is_lower_than(1, 30, 0):
            pytest.skip("This test requires Weaviate 1.30.0 or higher")
        randomUserName = "new-user" + str(random.randint(1, 1000))
        client.users.db.create(user_id=randomUserName)
        roles = client.users.get_assigned_roles(user_id=randomUserName)
        assert len(roles) == 0


def test_list_all_users(client_factory: ClientFactory) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=Auth.api_key("admin-key")) as client:
        if client._connection._weaviate_version.is_lower_than(1, 30, 0):
            pytest.skip("This test requires Weaviate 1.30.0 or higher")

        for i in range(5):
            client.users.db.delete(user_id=f"new-user-{i}")
            client.users.db.create(user_id=f"new-user-{i}")

        users = client.users.db.list_all()
        dynamic_users = [user for user in users if user.DbUserType == "dynamic"]
        assert len(dynamic_users) == 5
