import pytest

import weaviate
from integration.conftest import ClientFactory
from weaviate.auth import Auth
from weaviate.namespaces.models import Namespace
from weaviate.rbac.models import Permissions

NS_PORTS = (8094, 50064)
ADMIN_KEY = Auth.api_key("admin-key")

_MINIMUM_VERSION = (1, 38, 0)


def _skip_if_unsupported(client: weaviate.WeaviateClient) -> None:
    major, minor, patch = _MINIMUM_VERSION
    if client._connection._weaviate_version.is_lower_than(major, minor, patch):
        pytest.skip(f"Namespaces require Weaviate {major}.{minor}.{patch}+")


def test_create_and_get_namespace(client_factory: ClientFactory) -> None:
    with client_factory(ports=NS_PORTS, auth_credentials=ADMIN_KEY) as client:
        _skip_if_unsupported(client)

        client.namespaces.create(name="testns")
        try:
            ns = client.namespaces.get(name="testns")
            assert ns is not None
            assert isinstance(ns, Namespace)
            assert ns.name == "testns"
        finally:
            client.namespaces.delete(name="testns")


def test_get_nonexistent_namespace_returns_none(client_factory: ClientFactory) -> None:
    with client_factory(ports=NS_PORTS, auth_credentials=ADMIN_KEY) as client:
        _skip_if_unsupported(client)

        result = client.namespaces.get(name="doesnotexist")
        assert result is None


def test_list_namespaces(client_factory: ClientFactory) -> None:
    with client_factory(ports=NS_PORTS, auth_credentials=ADMIN_KEY) as client:
        _skip_if_unsupported(client)

        client.namespaces.create(name="listns1")
        client.namespaces.create(name="listns2")
        try:
            namespaces = client.namespaces.list_all()
            names = [ns.name for ns in namespaces]
            assert "listns1" in names
            assert "listns2" in names
        finally:
            client.namespaces.delete(name="listns1")
            client.namespaces.delete(name="listns2")


def test_delete_namespace(client_factory: ClientFactory) -> None:
    with client_factory(ports=NS_PORTS, auth_credentials=ADMIN_KEY) as client:
        _skip_if_unsupported(client)

        client.namespaces.create(name="deletens")
        client.namespaces.delete(name="deletens")

        fetched = client.namespaces.get(name="deletens")
        assert fetched is None


def test_create_namespaced_user(client_factory: ClientFactory) -> None:
    with client_factory(ports=NS_PORTS, auth_credentials=ADMIN_KEY) as client:
        _skip_if_unsupported(client)

        client.namespaces.create(name="usernstest")
        # On namespace-enabled clusters the server qualifies the userId as
        # "namespace:user_id" in storage. Operators must use that qualified form
        # when calling get/delete.
        qualified_id = "usernstest:nsuser1"
        try:
            api_key = client.users.db.create(user_id="nsuser1", namespace="usernstest")
            assert isinstance(api_key, str)
            assert len(api_key) > 0

            user = client.users.db.get(user_id=qualified_id)
            assert user is not None
            assert user.user_id == qualified_id
            assert user.namespace == "usernstest"
        finally:
            client.users.db.delete(user_id=qualified_id)
            client.namespaces.delete(name="usernstest")


def test_namespace_permission_manage(client_factory: ClientFactory) -> None:
    with client_factory(ports=NS_PORTS, auth_credentials=ADMIN_KEY) as client:
        _skip_if_unsupported(client)

        client.roles.create(
            role_name="ns-manager",
            permissions=Permissions.namespaces(namespace="*", manage=True),
        )
        try:
            fetched = client.roles.get(role_name="ns-manager")
            assert fetched is not None
            assert any(p.namespace == "*" for p in fetched.namespaces_permissions)
        finally:
            client.roles.delete("ns-manager")


def test_namespace_permission_multiple_namespaces(
    client_factory: ClientFactory,
) -> None:
    with client_factory(ports=NS_PORTS, auth_credentials=ADMIN_KEY) as client:
        _skip_if_unsupported(client)

        client.roles.create(
            role_name="ns-multi",
            permissions=Permissions.namespaces(namespace=["ns1", "ns2"], manage=True),
        )
        try:
            fetched = client.roles.get(role_name="ns-multi")
            assert fetched is not None
            ns_names = {p.namespace for p in fetched.namespaces_permissions}
            assert "ns1" in ns_names
            assert "ns2" in ns_names
        finally:
            client.roles.delete("ns-multi")
