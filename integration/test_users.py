import pytest
from _pytest.fixtures import SubRequest

import weaviate
from integration.conftest import ClientFactory, _sanitize_collection_name
from weaviate.auth import Auth
from weaviate.rbac.models import Role, RoleBase, UserTypes

RBAC_PORTS = (8092, 50063)
RBAC_AUTH_CREDS = Auth.api_key("admin-key")


def _unique_user_id(name: str) -> str:
    return _sanitize_collection_name(name).lower()


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


def test_create_user_and_get(client_factory: ClientFactory, request: SubRequest) -> None:
    with client_factory(ports=(RBAC_PORTS), auth_credentials=Auth.api_key("admin-key")) as client:
        if client._connection._weaviate_version.is_lower_than(1, 30, 0):
            pytest.skip("This test requires Weaviate 1.30.0 or higher")

        user_id = _unique_user_id(request.node.name)
        api_key = client.users.db.create(user_id=user_id)
        with weaviate.connect_to_local(
            port=RBAC_PORTS[0], grpc_port=RBAC_PORTS[1], auth_credentials=Auth.api_key(api_key)
        ) as client2:
            user = client2.users.get_my_user()
            assert user.user_id == user_id
        dynamic_user = client.users.db.get(user_id=user_id)
        assert dynamic_user is not None
        assert dynamic_user.user_id == user_id
        assert dynamic_user.user_type == UserTypes.DB_DYNAMIC
        assert client.users.db.delete(user_id=user_id)


def test_delete_user(client_factory: ClientFactory, request: SubRequest) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=Auth.api_key("admin-key")) as client:
        if client._connection._weaviate_version.is_lower_than(1, 30, 0):
            pytest.skip("This test requires Weaviate 1.30.0 or higher")

        user_id = _unique_user_id(request.node.name)
        client.users.db.create(user_id=user_id)
        assert client.users.db.delete(user_id=user_id)

        assert not client.users.db.delete(user_id="I-do-not-exist")


def test_rotate_user_key(client_factory: ClientFactory, request: SubRequest) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=Auth.api_key("admin-key")) as client:
        if client._connection._weaviate_version.is_lower_than(1, 30, 0):
            pytest.skip("This test requires Weaviate 1.30.0 or higher")

        user_id = _unique_user_id(request.node.name)
        api_key = client.users.db.create(user_id=user_id)
        with weaviate.connect_to_local(
            port=RBAC_PORTS[0], grpc_port=RBAC_PORTS[1], auth_credentials=Auth.api_key(api_key)
        ) as client2:
            user = client2.users.get_my_user()
            assert user.user_id == user_id

        api_key_new = client.users.db.rotate_key(user_id=user_id)
        with weaviate.connect_to_local(
            port=RBAC_PORTS[0], grpc_port=RBAC_PORTS[1], auth_credentials=Auth.api_key(api_key_new)
        ) as client2:
            user = client2.users.get_my_user()
            assert user.user_id == user_id

        assert client.users.db.delete(user_id=user_id)


def test_de_activate(client_factory: ClientFactory, request: SubRequest) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=Auth.api_key("admin-key")) as client:
        if client._connection._weaviate_version.is_lower_than(1, 30, 0):
            pytest.skip("This test requires Weaviate 1.30.0 or higher")

        user_id = _unique_user_id(request.node.name)
        client.users.db.create(user_id=user_id)

        assert client.users.db.deactivate(user_id=user_id)
        assert not client.users.db.deactivate(
            user_id=user_id
        )  # second deactivation returns a conflict => false
        user = client.users.db.get(user_id=user_id)
        assert not user.active
        assert client.users.db.activate(user_id=user_id)
        assert not client.users.db.activate(
            user_id=user_id
        )  # second activation returns a conflict => false
        user = client.users.db.get(user_id=user_id)
        assert user.active

        client.users.db.delete(user_id=user_id)


def test_deactivate_and_revoke(client_factory: ClientFactory, request: SubRequest) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=Auth.api_key("admin-key")) as client:
        if client._connection._weaviate_version.is_lower_than(1, 30, 0):
            pytest.skip("This test requires Weaviate 1.30.0 or higher")

        user_id = _unique_user_id(request.node.name)
        api_key_old = client.users.db.create(user_id=user_id)
        assert client.users.db.deactivate(user_id=user_id, revoke_key=True)

        with pytest.raises(weaviate.exceptions.UnexpectedStatusCodeError):
            weaviate.connect_to_local(
                port=RBAC_PORTS[0],
                grpc_port=RBAC_PORTS[1],
                auth_credentials=Auth.api_key(api_key_old),
            )

        # re-activating is not enough
        assert client.users.db.activate(user_id=user_id)
        with pytest.raises(weaviate.exceptions.UnexpectedStatusCodeError):
            weaviate.connect_to_local(
                port=RBAC_PORTS[0],
                grpc_port=RBAC_PORTS[1],
                auth_credentials=Auth.api_key(api_key_old),
            )

        api_key_new = client.users.db.rotate_key(user_id=user_id)

        with weaviate.connect_to_local(
            port=RBAC_PORTS[0], grpc_port=RBAC_PORTS[1], auth_credentials=Auth.api_key(api_key_new)
        ) as client2:
            user = client2.users.get_my_user()
            assert user.user_id == user_id

        client.users.db.delete(user_id=user_id)


def test_deprecated_syntax(client_factory: ClientFactory, request: SubRequest) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=Auth.api_key("admin-key")) as client:
        if client._connection._weaviate_version.is_lower_than(1, 30, 0):
            pytest.skip("This test requires Weaviate 1.30.0 or higher")
        user_id = _unique_user_id(request.node.name)
        client.users.db.create(user_id=user_id)
        roles = client.users.db.get_assigned_roles(user_id=user_id)
        assert len(roles) == 0
        client.users.db.delete(user_id=user_id)


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


def test_get_user_created_at_and_api_key_first_letters(
    client_factory: ClientFactory, request: SubRequest
) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=Auth.api_key("admin-key")) as client:
        if client._connection._weaviate_version.is_lower_than(1, 30, 0):
            pytest.skip("This test requires Weaviate 1.30.0 or higher")

        user_id = _unique_user_id(request.node.name)
        client.users.db.create(user_id=user_id)
        try:
            user = client.users.db.get(user_id=user_id)
            assert user is not None
            assert user.created_at is not None
            assert user.api_key_first_letters is not None
            assert len(user.api_key_first_letters) > 0
        finally:
            client.users.db.delete(user_id=user_id)


def test_get_user_include_last_used_time(
    client_factory: ClientFactory, request: SubRequest
) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=Auth.api_key("admin-key")) as client:
        if client._connection._weaviate_version.is_lower_than(1, 30, 0):
            pytest.skip("This test requires Weaviate 1.30.0 or higher")

        user_id = _unique_user_id(request.node.name)
        api_key = client.users.db.create(user_id=user_id)
        try:
            # log in with the new user to generate a lastUsedAt timestamp
            with weaviate.connect_to_local(
                port=RBAC_PORTS[0],
                grpc_port=RBAC_PORTS[1],
                auth_credentials=Auth.api_key(api_key),
            ) as client2:
                assert client2.users.get_my_user().user_id == user_id

            # without include_last_used_time, last_used_time should be None
            user = client.users.db.get(user_id=user_id)
            assert user is not None
            assert user.last_used_time is None

            # with include_last_used_time=True, last_used_time should be populated
            user = client.users.db.get(user_id=user_id, include_last_used_time=True)
            assert user is not None
            assert user.last_used_time is not None
        finally:
            client.users.db.delete(user_id=user_id)


def test_list_all_include_last_used_time(
    client_factory: ClientFactory, request: SubRequest
) -> None:
    with client_factory(ports=RBAC_PORTS, auth_credentials=Auth.api_key("admin-key")) as client:
        if client._connection._weaviate_version.is_lower_than(1, 30, 0):
            pytest.skip("This test requires Weaviate 1.30.0 or higher")

        user_id = _unique_user_id(request.node.name)
        api_key = client.users.db.create(user_id=user_id)
        try:
            # log in with the new user to generate a lastUsedAt timestamp
            with weaviate.connect_to_local(
                port=RBAC_PORTS[0],
                grpc_port=RBAC_PORTS[1],
                auth_credentials=Auth.api_key(api_key),
            ) as client2:
                assert client2.users.get_my_user().user_id == user_id

            # without include_last_used_time, last_used_time should be None
            users = client.users.db.list_all()
            target = next((u for u in users if u.user_id == user_id), None)
            assert target is not None
            assert target.created_at is not None
            assert target.api_key_first_letters is not None
            assert target.last_used_time is None

            # with include_last_used_time=True, last_used_time should be populated
            users = client.users.db.list_all(include_last_used_time=True)
            target = next((u for u in users if u.user_id == user_id), None)
            assert target is not None
            assert target.last_used_time is not None
        finally:
            client.users.db.delete(user_id=user_id)
