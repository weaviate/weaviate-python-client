import time

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


def _a_storage_candidate(client: weaviate.WeaviateClient) -> str:
    """Return a node name usable as a ``home_node`` (must be a real storage candidate)."""
    nodes = client.cluster.nodes()
    assert nodes, "expected at least one cluster node"
    return nodes[0].name


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


def test_create_namespace_with_home_node(client_factory: ClientFactory) -> None:
    with client_factory(ports=NS_PORTS, auth_credentials=ADMIN_KEY) as client:
        _skip_if_unsupported(client)

        home_node = _a_storage_candidate(client)
        ns = client.namespaces.create(name="homenodens", home_node=home_node)
        try:
            assert ns.name == "homenodens"
            assert ns.home_node == home_node
            assert ns.state == "active"

            fetched = client.namespaces.get(name="homenodens")
            assert fetched is not None
            assert fetched.home_node == home_node
        finally:
            client.namespaces.delete(name="homenodens")


def test_update_namespace_home_node(client_factory: ClientFactory) -> None:
    with client_factory(ports=NS_PORTS, auth_credentials=ADMIN_KEY) as client:
        _skip_if_unsupported(client)

        home_node = _a_storage_candidate(client)
        # Create without a home_node so the cluster auto-selects, then pin it explicitly.
        client.namespaces.create(name="updatens")
        try:
            updated = client.namespaces.update(name="updatens", home_node=home_node)
            assert updated.name == "updatens"
            assert updated.home_node == home_node

            fetched = client.namespaces.get(name="updatens")
            assert fetched is not None
            assert fetched.home_node == home_node
        finally:
            client.namespaces.delete(name="updatens")


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

        # Deletion is asynchronous: delete() returns 202 and the server marks the
        # namespace "deleting", then removes it on the background cleanup sweep
        # (NAMESPACE_CLEANUP_INTERVAL). Poll until it is gone.
        deadline = time.time() + 60
        fetched = client.namespaces.get(name="deletens")
        while fetched is not None and time.time() < deadline:
            assert fetched.state == "deleting"
            time.sleep(0.5)
            fetched = client.namespaces.get(name="deletens")
        assert fetched is None


def test_create_namespaced_user(client_factory: ClientFactory) -> None:
    with client_factory(ports=NS_PORTS, auth_credentials=ADMIN_KEY) as client:
        _skip_if_unsupported(client)

        client.namespaces.create(name="usernstest")
        # On namespace-enabled clusters an operator creates a user with a
        # namespace-qualified id "<namespace>:<user>"; the same qualified id is
        # used for get/delete.
        qualified_id = "usernstest:nsuser1"
        try:
            api_key = client.users.db.create(user_id=qualified_id)
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
