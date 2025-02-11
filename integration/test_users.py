import pytest

from integration.conftest import ClientFactory
from weaviate.auth import Auth


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
