from typing import Callable, Generator
from _pytest.fixtures import SubRequest

import pytest
import weaviate
from .conftest import _sanitize_collection_name


ClientFactory = Callable[[int, int], weaviate.WeaviateClient]


@pytest.fixture(scope="module")
def client_factory() -> Generator[Callable[[int, int], weaviate.WeaviateClient], None, None]:
    client: weaviate.WeaviateClient = None

    def maker(http: int, grpc: int) -> weaviate.WeaviateClient:
        nonlocal client
        client = weaviate.WeaviateClient(
            connection_params=weaviate.connect.ConnectionParams.from_url(
                f"http://localhost:{http}", grpc
            ),
            skip_init_checks=False,
        )
        client.connect()
        return client

    try:
        yield maker
    finally:
        assert client is not None
        client.close()


@pytest.fixture(scope="module")
def client(client_factory: ClientFactory) -> Generator[weaviate.WeaviateClient, None, None]:
    yield client_factory(8080, 50051)


def test_alias_creation_and_deletion(client: weaviate.WeaviateClient, request: SubRequest) -> None:
    name = _sanitize_collection_name(request.node.name)
    name2 = _sanitize_collection_name(request.node.name + "_2")

    client.collections.delete(name)
    client.collections.delete(name2)
    client.alias.delete(alias_name="Test_alias1")
    client.alias.delete(alias_name="Test_alias2")

    try:
        client.collections.create(name=name)
        client.collections.create(name=name2)

        client.alias.create(alias_name="Test_alias1", target_collection=name)
        client.alias.create(alias_name="Test_alias2", target_collection=name2)
        all_alias = client.alias.list_all()
        assert len(all_alias) == 2
        assert all_alias["Test_alias1"].alias == "Test_alias1"
        assert all_alias["Test_alias1"].collection == name

        collection_alias = client.alias.list_all(collection=name2)
        assert len(collection_alias) == 1
        assert collection_alias["Test_alias2"].alias == "Test_alias2"

        assert all_alias["Test_alias2"].alias == "Test_alias2"
        assert all_alias["Test_alias2"].collection == name2

        # Delete existing aliases
        assert client.alias.delete(alias_name="Test_alias1")
        assert client.alias.delete(alias_name="Test_alias2")
        all_alias = client.alias.list_all()
        assert len(all_alias) == 0

        assert not client.alias.delete(alias_name="Test_alias1")

    finally:
        client.collections.delete(name)
        client.collections.delete(name2)


def test_alias_creation_and_update(client: weaviate.WeaviateClient, request: SubRequest) -> None:
    name = _sanitize_collection_name(request.node.name)
    name2 = _sanitize_collection_name(request.node.name + "_2")

    client.collections.delete(name)
    client.collections.delete(name2)
    client.alias.delete(alias_name="Test_alias1")
    client.alias.delete(alias_name="Test_alias2")

    try:
        client.collections.create(name=name)
        client.collections.create(name=name2)

        client.alias.create(alias_name="Test_alias1", target_collection=name)
        all_alias = client.alias.list_all()
        assert len(all_alias) == 1
        assert all_alias["Test_alias1"].alias == "Test_alias1"
        assert all_alias["Test_alias1"].collection == name

        assert client.alias.update(alias_name="Test_alias1", new_target_collection=name2)
        all_alias = client.alias.list_all()
        assert all_alias["Test_alias1"].alias == "Test_alias1"
        assert all_alias["Test_alias1"].collection == name2

        # return status code not yet correct
        # assert not client.alias.update(alias_name="does_not_exist", new_target_collection=name2)
    finally:
        client.collections.delete(name)
        client.collections.delete(name2)
        client.alias.delete(alias_name="Test_alias1")
        client.alias.delete(alias_name="Test_alias2")


def test_alias_get(client: weaviate.WeaviateClient, request: SubRequest) -> None:
    name = _sanitize_collection_name(request.node.name)

    client.collections.delete(name)
    client.alias.delete(alias_name="Test_alias1")
    try:
        client.collections.create(name=name)

        client.alias.create(alias_name="Test_alias1", target_collection=name)
        alias = client.alias.get(alias_name="Test_alias1")
        assert alias is not None
        assert alias.alias == "Test_alias1"
        assert alias.collection == name
    finally:
        client.collections.delete(name)
        client.alias.delete(alias_name="Test_alias1")
