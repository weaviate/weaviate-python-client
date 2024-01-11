from typing import Generator

import pytest
from _pytest.fixtures import SubRequest
from weaviate import WeaviateStartUpError

import weaviate
from weaviate import Collection
from weaviate.collections.classes.config import Configure, _CollectionConfig

WCS_HOST = "piblpmmdsiknacjnm1ltla.c1.europe-west3.gcp.weaviate.cloud"
WCS_URL = f"https://{WCS_HOST}"
WCS_GRPC_HOST = f"grpc-{WCS_HOST}"
WCS_CREDS = weaviate.AuthApiKey("cy4ua772mBlMdfw3YnclqAWzFhQt0RLIN0sl")


@pytest.fixture(scope="module")
def client() -> Generator[weaviate.WeaviateClient, None, None]:
    client = weaviate.WeaviateClient(
        connection_params=weaviate.ConnectionParams.from_url("http://localhost:8080", 50051),
        skip_init_checks=False,
    )
    yield client


def test_fail_to_connect_to_inactive_grpc_port() -> None:
    with pytest.raises(weaviate.exceptions.WeaviateGRPCUnavailableError):
        weaviate.WeaviateClient(
            connection_params=weaviate.ConnectionParams.from_url("http://localhost:8080", 12345),
            skip_init_checks=False,
        )


def test_fail_to_connect_to_unspecified_grpc_port() -> None:
    with pytest.raises(weaviate.exceptions.WeaviateGRPCUnavailableError):
        weaviate.WeaviateClient(
            connection_params=weaviate.ConnectionParams.from_url("http://localhost:8080"),
            skip_init_checks=False,
        )


def test_fail_to_connect_with_bad_wcs_url() -> None:
    with pytest.raises(WeaviateStartUpError):
        weaviate.connect_to_wcs(
            WCS_URL + "bad",
            auth_credentials=WCS_CREDS,
        )


@pytest.mark.parametrize(
    "bad_config",
    [
        {
            "http_secure": False,
            "http_host": WCS_HOST,
            "http_port": 443,
            "grpc_secure": True,
            "grpc_host": WCS_GRPC_HOST,
            "grpc_port": 443,
        },
        {
            "http_secure": True,
            "http_host": WCS_HOST,
            "http_port": 80,
            "grpc_secure": True,
            "grpc_host": WCS_GRPC_HOST,
            "grpc_port": 443,
        },
        {
            "http_secure": True,
            "http_host": WCS_HOST + "bad",
            "http_port": 443,
            "grpc_secure": True,
            "grpc_host": WCS_GRPC_HOST,
            "grpc_port": 443,
        },
    ],
)
def test_fail_to_connect_with_bad_custom_wcs_setup_rest(bad_config: dict) -> None:
    with pytest.raises(WeaviateStartUpError):
        weaviate.connect_to_custom(**bad_config, auth_credentials=WCS_CREDS)


@pytest.mark.parametrize(
    "bad_config",
    [
        {
            "http_secure": True,
            "http_host": WCS_HOST,
            "http_port": 443,
            "grpc_secure": False,
            "grpc_host": WCS_GRPC_HOST,
            "grpc_port": 443,
        },
        {
            "http_secure": True,
            "http_host": WCS_HOST,
            "http_port": 443,
            "grpc_secure": True,
            "grpc_host": WCS_GRPC_HOST + "bad",
            "grpc_port": 443,
        },
        {
            "http_secure": True,
            "http_host": WCS_HOST,
            "http_port": 443,
            "grpc_secure": True,
            "grpc_host": WCS_GRPC_HOST,
            "grpc_port": 80,
        },
    ],
)
def test_fail_to_connect_with_bad_custom_wcs_setup_grpc(bad_config: dict) -> None:
    with pytest.raises(weaviate.exceptions.WeaviateGRPCUnavailableError):
        weaviate.connect_to_custom(**bad_config, auth_credentials=WCS_CREDS)


def test_fail_to_connect_with_bad_custom_wcs_setup_rest_and_grpc() -> None:
    """Test that REST checks take precendence to gRPC checks by throwing REST error rather than gRPC error."""
    with pytest.raises(WeaviateStartUpError):
        weaviate.connect_to_custom(
            http_secure=True,
            http_host=WCS_HOST + "bad",
            http_port=443,
            grpc_secure=True,
            grpc_host=WCS_GRPC_HOST + "bad",
            grpc_port=443,
            auth_credentials=WCS_CREDS,
        )


def test_connect_to_wcs() -> None:
    client = weaviate.connect_to_wcs(
        "https://piblpmmdsiknacjnm1ltla.c1.europe-west3.gcp.weaviate.cloud",
        auth_credentials=WCS_CREDS,
    )
    client.get_meta()


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


def test_client_cluster(client: weaviate.WeaviateClient, request: SubRequest) -> None:
    client.collections.delete(request.node.name)
    collection = client.collections.create(name=request.node.name)

    nodes = client.cluster.nodes(collection.name, output="verbose")
    assert len(nodes) == 1
    assert len(nodes[0].shards) == 1
    assert nodes[0].shards[0].collection == collection.name
