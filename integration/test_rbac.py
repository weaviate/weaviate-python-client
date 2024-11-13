import pytest

from integration.conftest import ClientFactory
from weaviate.auth import Auth
from weaviate.rbac.models import RBAC


def test_create_role(client_factory: ClientFactory) -> None:
    with client_factory(
        ports=(8092, 50063), auth_credentials=Auth.api_key("jp-secret-key")
    ) as client:
        if client._connection._weaviate_version.is_lower_than(1, 28, 0):
            pytest.skip("This test requires Weaviate 1.28.0 or higher")
        client.roles.create(
            name="CollectionCreator",
            permissions=RBAC.permissions.collection(
                collection="*", actions=RBAC.actions.collection.CREATE_COLLECTIONS
            ),
        )
        role = client.roles.by_name("CollectionCreator")
        assert role is not None
        assert role.name == "CollectionCreator"
        assert role.collections_permissions is not None
        assert len(role.collections_permissions) == 1
        assert role.collections_permissions[0] == RBAC.actions.collection.CREATE_COLLECTIONS
