from typing import Callable, Generator, Optional
from _pytest.fixtures import SubRequest

import pytest
import weaviate
import weaviate.classes as wvc
from .conftest import _sanitize_collection_name


ClientFactory = Callable[[int, int], weaviate.WeaviateClient]


@pytest.fixture(scope="module")
def client_factory() -> Generator[Callable[[int, int], weaviate.WeaviateClient], None, None]:
    client: Optional[weaviate.WeaviateClient] = None

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
    if client._connection._weaviate_version.is_lower_than(1, 32, 0):
        pytest.skip("Aliases are not supported in Weaviate versions < 1.32.0")
    name = _sanitize_collection_name(request.node.name)
    name2 = _sanitize_collection_name(request.node.name + "_2")
    alias1: str = "Alias" + _sanitize_collection_name(request.node.name)
    alias2: str = "Alias" + _sanitize_collection_name(request.node.name + "_2")

    client.collections.delete(name)
    client.collections.delete(name2)
    client.alias.delete(alias_name=alias1)
    client.alias.delete(alias_name=alias2)

    try:
        client.collections.create(
            name=name, vectorizer_config=wvc.config.Configure.Vectorizer.none()
        )
        client.collections.create(
            name=name2, vectorizer_config=wvc.config.Configure.Vectorizer.none()
        )

        client.alias.create(alias_name=alias1, target_collection=name)
        client.alias.create(alias_name=alias2, target_collection=name2)
        all_alias = client.alias.list_all()
        all_alias = {
            alias[0]: alias[1]
            for alias in all_alias.items()
            if alias[1].collection in [name, name2]
        }
        assert len(all_alias) == 2
        assert all_alias[alias1].alias == alias1
        assert all_alias[alias1].collection == name

        collection_alias = client.alias.list_all(collection=name2)
        assert len(collection_alias) == 1
        assert collection_alias[alias2].alias == alias2

        assert all_alias[alias2].alias == alias2
        assert all_alias[alias2].collection == name2

        # Delete existing aliases
        if client.alias.exists(alias_name=alias1):
            assert client.alias.delete(alias_name=alias1)
        if client.alias.exists(alias_name=alias2):
            assert client.alias.delete(alias_name=alias2)
        all_alias = client.alias.list_all(collection=name2)
        all_alias = {
            alias[0]: alias[1]
            for alias in all_alias.items()
            if alias[1].collection in [name, name2]
        }
        assert len(all_alias) == 0

        assert not client.alias.delete(alias_name=alias1)

    finally:
        client.collections.delete(name)
        client.collections.delete(name2)


def test_alias_creation_and_update(client: weaviate.WeaviateClient, request: SubRequest) -> None:
    if client._connection._weaviate_version.is_lower_than(1, 32, 0):
        pytest.skip("Aliases are not supported in Weaviate versions < 1.32.0")

    name = _sanitize_collection_name(request.node.name)
    name2 = _sanitize_collection_name(request.node.name + "_2")
    alias1: str = "Alias" + _sanitize_collection_name(request.node.name)

    client.collections.delete(name)
    client.collections.delete(name2)
    client.alias.delete(alias_name=alias1)

    try:
        client.collections.create(
            name=name, vectorizer_config=wvc.config.Configure.Vectorizer.none()
        )
        client.collections.create(
            name=name2, vectorizer_config=wvc.config.Configure.Vectorizer.none()
        )

        client.alias.create(alias_name=alias1, target_collection=name)
        alias = client.alias.get(alias_name=alias1)
        assert alias is not None
        assert alias.alias == alias1
        assert alias.collection == name

        assert client.alias.update(alias_name=alias1, new_target_collection=name2)
        alias = client.alias.get(alias_name=alias1)
        assert alias is not None
        assert alias.alias == alias1
        assert alias.collection == name2

        # return status code not yet correct
        assert not client.alias.update(alias_name="does_not_exist", new_target_collection=name2)
    finally:
        client.collections.delete(name)
        client.collections.delete(name2)
        client.alias.delete(alias_name=alias1)


def test_alias_get(client: weaviate.WeaviateClient, request: SubRequest) -> None:
    if client._connection._weaviate_version.is_lower_than(1, 32, 0):
        pytest.skip("Aliases are not supported in Weaviate versions < 1.32.0")

    name = _sanitize_collection_name(request.node.name)
    alias1: str = "Alias" + _sanitize_collection_name(request.node.name)

    client.collections.delete(name)
    client.alias.delete(alias_name=alias1)
    try:
        client.collections.create(
            name=name, vectorizer_config=wvc.config.Configure.Vectorizer.none()
        )

        client.alias.create(alias_name=alias1, target_collection=name)
        alias = client.alias.get(alias_name=alias1)
        assert alias is not None
        assert alias.alias == alias1
        assert alias.collection == name
    finally:
        client.collections.delete(name)
        client.alias.delete(alias_name=alias1)


def test_alias_exists(client: weaviate.WeaviateClient, request: SubRequest) -> None:
    if client._connection._weaviate_version.is_lower_than(1, 32, 0):
        pytest.skip("Aliases are not supported in Weaviate versions < 1.32.0")

    name = _sanitize_collection_name(request.node.name)
    alias1: str = "Alias" + _sanitize_collection_name(request.node.name)

    client.collections.delete(name)
    client.alias.delete(alias_name=alias1)
    try:
        client.collections.create(
            name=name, vectorizer_config=wvc.config.Configure.Vectorizer.none()
        )

        client.alias.create(alias_name=alias1, target_collection=name)
        assert client.alias.exists(alias_name=alias1)
    finally:
        client.collections.delete(name)
        client.alias.delete(alias_name=alias1)
        assert not client.alias.exists(alias_name=alias1)
