from weaviate.rbac.permissions import RBAC
from weaviate.connect.helpers import connect_to_local


def test_rbac() -> None:
    with connect_to_local() as client:
        # Creating roles at the client level
        client.roles.create(
            name="BooksReader",
            permissions=[
                RBAC.permissions.collection("Books", RBAC.actions.collection.READ_OBJECT),
            ],
        )
        client.roles.create(
            name="BooksAdmin",
            permissions=[
                RBAC.permissions.collection("Books", [RBAC.actions.collection.CREATE_TENANT]),
                RBAC.permissions.collection("Authors", [RBAC.actions.collection.CREATE_OBJECT]),
            ],
        )
        client.roles.create(
            name="Reader",
            permissions=RBAC.permissions.database(RBAC.actions.database.CREATE_COLLECTION),
        )

        # Granting permissions at the client level
        client.roles.permissions.add(
            role="BooksReader",
            permissions=RBAC.permissions.collection("Books", RBAC.actions.collection.CREATE_OBJECT),
        )
        client.roles.permissions.remove(
            role="BooksAdmin",
            permissions=RBAC.permissions.collection(
                "Books", [RBAC.actions.collection.CREATE_TENANT]
            ),
        )

        # Assigning/revoking roles to users at the client level
        client.roles.assign(user="user1", roles="BooksReader")
        client.roles.revoke(user="user2", roles="BooksAdmin")

        # Inpsecting roles at the client level
        books_reader = client.roles.by_name("BooksReader")
        assert books_reader is not None
        assert books_reader.name == "BooksReader"

        assert books_reader.collection_permissions is not None
        assert len(books_reader.collection_permissions) == 1
        assert books_reader.collection_permissions[0].collection == "Books"
        assert len(books_reader.collection_permissions[0].actions) == 2

        assert books_reader.database_permissions is None
