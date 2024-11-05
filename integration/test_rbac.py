from integration.conftest import ClientFactory
from weaviate.auth import Auth
from weaviate.rbac.types import RBAC


def test_rbac(client_factory: ClientFactory) -> None:
    with client_factory(
        ports=(8080, 50051), auth_credentials=Auth.api_key("jp-secret-key")
    ) as client:
        client.roles.create(
            name="CollectionCreator",
            permissions=RBAC.permissions.database(actions=RBAC.actions.database.CREATE_COLLECTION),
        )
        roles = client.roles.list_all()
        assert len(roles) == 1
        assert roles[0].name == "CollectionCreator"
        assert roles[0].database_permissions is not None
        assert roles[0].database_permissions[0].actions == [RBAC.actions.database.CREATE_COLLECTION]
