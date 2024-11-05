from integration.conftest import ClientFactory
from weaviate.auth import Auth
from weaviate.rbac.models import RBAC


def test_create_role(client_factory: ClientFactory) -> None:
    with client_factory(
        ports=(8092, 50063), auth_credentials=Auth.api_key("jp-secret-key")
    ) as client:
        client.roles.create(
            name="CollectionCreator",
            permissions=RBAC.permissions.database(actions=RBAC.actions.database.CREATE_COLLECTION),
        )
        role = client.roles.by_name("CollectionCreator")
        assert role is not None
        assert role.name == "CollectionCreator"
        assert role.database_permissions is not None
        assert len(role.database_permissions) == 1
        assert role.database_permissions[0].actions == [RBAC.actions.database.CREATE_COLLECTION]