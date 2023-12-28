from typing import Generator

import pytest
from _pytest.fixtures import SubRequest

import weaviate
from weaviate import Collection
from weaviate.collections.classes.config import Configure, _CollectionConfig


@pytest.fixture(scope="module")
def client() -> Generator[weaviate.WeaviateClient, None, None]:
    client = weaviate.WeaviateClient(
        connection_params=weaviate.ConnectionParams.from_url("http://localhost:8080", 50051),
        skip_init_checks=False,
    )
    yield client


def test_fail_to_connect_to_inactive_grpc_port() -> None:
    with pytest.raises(weaviate.exceptions.WeaviateGrpcUnavailable):
        weaviate.WeaviateClient(
            connection_params=weaviate.ConnectionParams.from_url("http://localhost:8080", 12345),
            skip_init_checks=False,
        )


def test_fail_to_connect_to_unspecified_grpc_port() -> None:
    with pytest.raises(weaviate.exceptions.WeaviateGrpcUnavailable):
        weaviate.WeaviateClient(
            connection_params=weaviate.ConnectionParams.from_url("http://localhost:8080"),
            skip_init_checks=False,
        )


def test_create_get_and_delete(client: weaviate.WeaviateClient, request: SubRequest) -> None:
    name = request.node.name
    col = client.collections.create(name=name)
    assert client.collections.exists(name)
    assert isinstance(col, Collection)

    col = client.collections.get(name)
    assert isinstance(col, Collection)

    client.collections.delete(name)
    assert not client.collections.exists(name)


def test_delete_multiple(client: weaviate.WeaviateClient, request: SubRequest) -> None:
    name1 = request.node.name
    name2 = request.node.name + "2"
    client.collections.create(
        name=name1,
        vectorizer_config=Configure.Vectorizer.none(),
    )
    client.collections.create(
        name=name2,
        vectorizer_config=Configure.Vectorizer.none(),
    )
    assert client.collections.exists(name1)
    assert client.collections.exists(name2)

    client.collections.delete([name1, name2])
    assert not client.collections.exists(name1)
    assert not client.collections.exists(name2)


def test_create_raw_get_and_delete(client: weaviate.WeaviateClient, request: SubRequest) -> None:
    name = request.node.name
    col = client.collections.create_from_dict(
        {
            "class": name,
            "properties": [{"name": "Name", "dataType": ["text"]}],
            "vectorizer": "none",
        }
    )
    assert client.collections.exists(name)
    assert isinstance(col, Collection)

    col = client.collections.get(name)
    assert isinstance(col, Collection)

    client.collections.delete(name)
    assert not client.collections.exists(name)


def test_create_export_and_recreate(client: weaviate.WeaviateClient, request: SubRequest) -> None:
    name1 = request.node.name
    name2 = request.node.name + "2"
    col = client.collections.create(
        name=name1,
        vectorizer_config=Configure.Vectorizer.none(),
    )
    assert client.collections.exists(name1)
    assert isinstance(col, Collection)

    export = client.collections.export_config(name1)
    assert isinstance(export, _CollectionConfig)
    export.name = name2

    col = client.collections.create_from_config(export)
    assert client.collections.exists(name2)
    assert isinstance(col, Collection)

    client.collections.delete([name1, name2])
    assert not client.collections.exists(name1)
    assert not client.collections.exists(name2)


def test_collection_name_capitalization(
    client: weaviate.WeaviateClient, request: SubRequest
) -> None:
    name_small = "collectionCapitalizationTest"
    name_big = "CollectionCapitalizationTest"
    collection = client.collections.create(
        name=name_small,
        vectorizer_config=Configure.Vectorizer.none(),
    )

    assert collection.name == name_big
    client.collections.delete(name_small)
    assert not client.collections.exists(name_small)
    assert not client.collections.exists(name_big)
