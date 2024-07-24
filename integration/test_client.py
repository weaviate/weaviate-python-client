from typing import Callable, Generator, Tuple, Union

import pytest
from _pytest.fixtures import SubRequest

import weaviate
from weaviate.collections import Collection
from weaviate.collections.classes.config import (
    Configure,
    _CollectionConfig,
    DataType,
    GenerativeSearches,
    Property,
    ReferenceProperty,
    Vectorizers,
)
from weaviate.exceptions import WeaviateClosedClientError, WeaviateStartUpError
import weaviate.classes as wvc

from weaviate.config import Timeout

WCS_HOST = "piblpmmdsiknacjnm1ltla.c1.europe-west3.gcp.weaviate.cloud"
WCS_URL = f"https://{WCS_HOST}"
WCS_GRPC_HOST = f"grpc-{WCS_HOST}"
WCS_CREDS = wvc.init.Auth.api_key("cy4ua772mBlMdfw3YnclqAWzFhQt0RLIN0sl")

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


def test_fail_to_connect_to_inactive_grpc_port() -> None:
    with pytest.raises(weaviate.exceptions.WeaviateGRPCUnavailableError):
        weaviate.WeaviateClient(
            connection_params=weaviate.connect.ConnectionParams.from_url(
                "http://localhost:8080", 12345
            ),
            skip_init_checks=False,
        ).connect()


def test_fail_to_connect_with_bad_wcs_url() -> None:
    with pytest.raises(WeaviateStartUpError):
        weaviate.connect_to_wcs(
            WCS_URL + "bad",
            auth_credentials=WCS_CREDS,
        ).connect()


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
    with weaviate.connect_to_wcs(
        "https://piblpmmdsiknacjnm1ltla.c1.europe-west3.gcp.weaviate.cloud",
        auth_credentials=WCS_CREDS,
    ) as client:
        client.get_meta()


def test_create_get_and_delete(client: weaviate.WeaviateClient, request: SubRequest) -> None:
    name = request.node.name
    client.collections.delete(name)

    col = client.collections.create(name=name, vectorizer_config=Configure.Vectorizer.none())
    assert client.collections.exists(name)
    assert isinstance(col, Collection)

    col = client.collections.get(name)
    assert isinstance(col, Collection)

    client.collections.delete(name)
    assert not client.collections.exists(name)


def test_delete_multiple(client: weaviate.WeaviateClient, request: SubRequest) -> None:
    name1 = request.node.name
    name2 = request.node.name + "2"
    client.collections.delete([name1, name2])

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
    client.collections.delete([name1, name2])

    col = client.collections.create(
        name=name1,
        vectorizer_config=Configure.Vectorizer.text2vec_contextionary(
            vectorize_collection_name=False
        ),
        generative_config=Configure.Generative.cohere(model="something", k=10),
        properties=[
            Property(
                name="name",
                data_type=DataType.TEXT,
                description="desc",
                index_filterable=True,
                index_searchable=True,
                skip_vectorization=True,
                vectorize_property_name=True,
            ),
            Property(
                name="name_vectorized",
                data_type=DataType.TEXT,
                description="desc",
                index_filterable=True,
                index_searchable=True,
                skip_vectorization=False,
                vectorize_property_name=False,
            ),
        ],
        references=[ReferenceProperty(name="ref", target_collection=name1)],
    )
    assert client.collections.exists(name1)
    assert isinstance(col, Collection)

    export = client.collections.export_config(name1)
    assert isinstance(export, _CollectionConfig)
    export.name = name2

    col = client.collections.create_from_config(export)
    assert client.collections.exists(name2)
    assert isinstance(col, Collection)
    export = client.collections.export_config(name2)
    assert len(export.properties) == 2
    assert export.properties[0].description == "desc"
    assert len(export.references) == 1
    assert export.properties[0].index_searchable
    assert export.vectorizer_config is not None
    assert export.vectorizer_config.vectorizer == Vectorizers.TEXT2VEC_CONTEXTIONARY
    assert not export.vectorizer_config.vectorize_collection_name

    assert export.generative_config is not None
    assert export.generative_config.generative == GenerativeSearches.COHERE
    assert export.generative_config.model["model"] == "something"
    assert export.generative_config.model["kProperty"] == 10

    client.collections.delete([name1, name2])
    assert not client.collections.exists(name1)
    assert not client.collections.exists(name2)


def test_create_export_and_recreate_named_vectors(
    client: weaviate.WeaviateClient, request: SubRequest
) -> None:
    if client._connection._weaviate_version.is_lower_than(1, 24, 0):
        pytest.skip("Named vectors are not supported in versions lower than 1.24.0")

    name1 = request.node.name
    name2 = request.node.name + "2"
    client.collections.delete([name1, name2])

    col = client.collections.create(
        name=name1,
        properties=[
            Property(
                name="name",
                data_type=DataType.TEXT,
                vectorize_property_name=True,
            ),
        ],
        vectorizer_config=[
            Configure.NamedVectors.text2vec_contextionary(
                "name",
                source_properties=["name"],
                vectorize_collection_name=False,
            ),
            Configure.NamedVectors.none("custom", vector_index_config=Configure.VectorIndex.flat()),
        ],
    )
    conf = col.config.get()
    conf.name = name2

    col2 = client.collections.create_from_config(conf)

    conf2 = col2.config.get()
    assert conf2.vector_config == conf.vector_config

    client.collections.delete([name1, name2])


def test_collection_name_capitalization(
    client: weaviate.WeaviateClient, request: SubRequest
) -> None:
    name_small = "collectionCapitalizationTest"
    name_big = "CollectionCapitalizationTest"
    try:
        collection = client.collections.create(
            name=name_small,
            vectorizer_config=Configure.Vectorizer.none(),
        )
        assert collection.name == name_big
        client.collections.delete(name_small)
        assert not client.collections.exists(name_small)
        assert not client.collections.exists(name_big)
    finally:
        client.collections.delete(name_big)


def test_client_cluster_with_lazy_shard_loading(
    client: weaviate.WeaviateClient, request: SubRequest
) -> None:
    try:
        collection = client.collections.create(
            name=request.node.name, vectorizer_config=Configure.Vectorizer.none()
        )

        nodes = client.cluster.nodes(collection.name, output="verbose")
        assert len(nodes) == 1
        assert len(nodes[0].shards) == 1
        assert nodes[0].shards[0].collection == collection.name
        assert nodes[0].shards[0].object_count == 0
        assert nodes[0].shards[0].vector_indexing_status == "READY"
        assert nodes[0].shards[0].vector_queue_length == 0
        assert nodes[0].shards[0].compressed is False
        if collection._connection._weaviate_version.is_lower_than(1, 24, 0):
            assert nodes[0].shards[0].loaded is None
        else:
            assert nodes[0].shards[0].loaded is True
    finally:
        client.collections.delete(request.node.name)


def test_client_cluster_without_lazy_shard_loading(
    client_factory: ClientFactory, request: SubRequest
) -> None:
    client = client_factory(8090, 50061)
    try:
        collection = client.collections.create(
            name=request.node.name, vectorizer_config=Configure.Vectorizer.none()
        )

        nodes = client.cluster.nodes(collection.name, output="verbose")
        assert len(nodes) == 1
        assert len(nodes[0].shards) == 1
        assert nodes[0].shards[0].collection == collection.name
        assert nodes[0].shards[0].object_count == 0
        assert nodes[0].shards[0].vector_indexing_status == "READY"
        assert nodes[0].shards[0].vector_queue_length == 0
        assert nodes[0].shards[0].compressed is False
        if collection._connection._weaviate_version.is_lower_than(1, 24, 0):
            assert nodes[0].shards[0].loaded is None
        elif collection._connection._weaviate_version.is_lower_than(1, 25, 0):
            assert nodes[0].shards[0].loaded is True
        else:
            assert nodes[0].shards[0].loaded is False
    finally:
        client.collections.delete(request.node.name)


def test_client_cluster_multitenant(client: weaviate.WeaviateClient, request: SubRequest) -> None:
    try:
        collection = client.collections.create(
            name=request.node.name,
            multi_tenancy_config=Configure.multi_tenancy(enabled=True),
            vectorizer_config=Configure.Vectorizer.none(),
        )

        nodes = client.cluster.nodes(collection.name, output="verbose")
        assert len(nodes) == 1
        assert len(nodes[0].shards) == 0
    finally:
        client.collections.delete(request.node.name)


def test_client_cluster_minimal(client: weaviate.WeaviateClient, request: SubRequest) -> None:
    try:
        collection = client.collections.create(
            name=request.node.name, vectorizer_config=Configure.Vectorizer.none()
        )

        nodes = client.cluster.nodes(collection.name, output="minimal")
        assert len(nodes) == 1
        assert nodes[0].shards is None
    finally:
        client.collections.delete(request.node.name)


def test_client_connect_and_close() -> None:
    client = weaviate.WeaviateClient(
        connection_params=weaviate.connect.ConnectionParams.from_url(
            "http://localhost:8080", 50051
        ),
        skip_init_checks=False,
    )
    client.connect()
    assert client.is_connected()
    client.get_meta()
    assert client.is_live()

    client.close()
    assert not client.is_connected()
    with pytest.raises(WeaviateClosedClientError):
        client.get_meta()


@pytest.mark.asyncio
async def test_async_client_connect_and_close() -> None:
    client = weaviate.WeaviateAsyncClient(
        connection_params=weaviate.connect.ConnectionParams.from_url(
            "http://localhost:8080", 50051
        ),
        skip_init_checks=False,
    )
    await client.connect()
    assert client.is_connected()
    await client.get_meta()
    assert await client.is_live()

    await client.close()
    assert not client.is_connected()
    with pytest.raises(WeaviateClosedClientError):
        await client.get_meta()


def test_client_as_context_manager() -> None:
    with weaviate.WeaviateClient(
        connection_params=weaviate.connect.ConnectionParams.from_url(
            "http://localhost:8080", 50051
        ),
        skip_init_checks=False,
    ) as client:
        assert client.is_connected()
        client.get_meta()
        assert client.is_live()

    assert not client.is_connected()
    with pytest.raises(WeaviateClosedClientError):
        client.get_meta()


@pytest.mark.asyncio
async def test_async_client_as_context_manager() -> None:
    async with weaviate.WeaviateAsyncClient(
        connection_params=weaviate.connect.ConnectionParams.from_url(
            "http://localhost:8080", 50051
        ),
        skip_init_checks=False,
    ) as client:
        assert client.is_connected()
        await client.get_meta()
        assert await client.is_live()

    assert not client.is_connected()
    with pytest.raises(WeaviateClosedClientError):
        await client.get_meta()


def test_connect_to_wrong_wcs() -> None:
    with pytest.raises(WeaviateStartUpError):
        weaviate.connect_to_wcs("does-not-exist", auth_credentials=WCS_CREDS, skip_init_checks=True)


def test_connect_to_wrong_local() -> None:
    with pytest.raises(expected_exception=WeaviateStartUpError):
        weaviate.connect_to_local("does-not-exist", skip_init_checks=True)


def test_connect_to_wrong_custom() -> None:
    with pytest.raises(expected_exception=WeaviateStartUpError):
        weaviate.connect_to_custom(
            "does-not-exist",
            http_port=1234,
            http_secure=False,
            grpc_host="does-not-exist",
            grpc_port=2345,
            grpc_secure=False,
            skip_init_checks=True,
        )


def test_rest_call_without_connect() -> None:
    client = weaviate.WeaviateClient(
        weaviate.connect.ConnectionParams.from_url("http://localhost:8080", 50051)
    )
    with pytest.raises(weaviate.exceptions.WeaviateClosedClientError):
        client.get_meta()


def test_grpc_call_without_connect() -> None:
    client = weaviate.WeaviateClient(
        weaviate.connect.ConnectionParams.from_url("http://localhost:8080", 50051)
    )
    with pytest.raises(weaviate.exceptions.WeaviateClosedClientError):
        client.collections.get("does-not-exist").query.fetch_objects()


def test_client_with_skip_init_check(request: SubRequest) -> None:
    with weaviate.connect_to_local(skip_init_checks=True) as client:
        client.collections.delete(request.node.name)
        col = client.collections.create(
            name=request.node.name,
            vectorizer_config=Configure.Vectorizer.none(),
            properties=[
                Property(name="name", data_type=DataType.TEXT),
                Property(name="age", data_type=DataType.INT),
            ],
        )

        col.data.insert(properties={"name": "Name"})

        obj = col.query.fetch_objects().objects[0]
        assert obj.properties["name"] == "Name"
        client.collections.delete(request.node.name)


@pytest.mark.parametrize("timeout", [(1, 2), Timeout(query=1, insert=2, init=2)])
def test_client_with_extra_options(timeout: Union[Tuple[int, int], Timeout]) -> None:
    additional_config = wvc.init.AdditionalConfig(timeout=timeout, trust_env=True)

    for client in [
        weaviate.connect_to_wcs(
            cluster_url=WCS_URL, auth_credentials=WCS_CREDS, additional_config=additional_config
        ),
        weaviate.connect_to_weaviate_cloud(
            cluster_url=WCS_URL, auth_credentials=WCS_CREDS, additional_config=additional_config
        ),
        weaviate.connect_to_local(additional_config=additional_config),
        weaviate.connect_to_custom(
            http_secure=True,
            http_host=WCS_HOST,
            http_port=443,
            grpc_secure=True,
            grpc_host=WCS_GRPC_HOST,
            grpc_port=443,
            auth_credentials=WCS_CREDS,
            additional_config=additional_config,
        ),
    ]:
        assert client._connection.timeout_config == Timeout(query=1, insert=2, init=2)
        client.close()


@pytest.mark.parametrize("timeout", [(1, 2), Timeout(query=1, insert=2, init=2)])
@pytest.mark.asyncio
async def test_async_client_with_extra_options(timeout: Union[Tuple[int, int], Timeout]) -> None:
    additional_config = wvc.init.AdditionalConfig(timeout=timeout, trust_env=True)

    for client in [
        weaviate.use_async_with_weaviate_cloud(
            cluster_url=WCS_URL,
            auth_credentials=WCS_CREDS,
            additional_config=additional_config,
        ),
        weaviate.use_async_with_local(additional_config=additional_config),
        weaviate.use_async_with_custom(
            http_secure=True,
            http_host=WCS_HOST,
            http_port=443,
            grpc_secure=True,
            grpc_host=WCS_GRPC_HOST,
            grpc_port=443,
            auth_credentials=WCS_CREDS,
            additional_config=additional_config,
        ),
    ]:
        await client.connect()
        await client.get_meta()
        assert client._connection.timeout_config == Timeout(query=1, insert=2, init=2)
        await client.close()


def test_client_error_for_wcs_without_auth() -> None:
    with pytest.raises(weaviate.exceptions.AuthenticationFailedError) as e:
        weaviate.connect_to_wcs(cluster_url=WCS_URL, auth_credentials=None)
        assert "wvc.init.Auth.api_key" in e.value.message


def test_client_is_not_ready() -> None:
    assert not weaviate.WeaviateClient(
        connection_params=weaviate.connect.ConnectionParams.from_url(
            "http://localhost:8080", 50051
        ),
        skip_init_checks=True,
    ).is_ready()


def test_client_is_ready() -> None:
    with weaviate.connect_to_wcs(
        cluster_url=WCS_URL, auth_credentials=WCS_CREDS, skip_init_checks=True
    ) as client:
        assert client.is_ready()


@pytest.mark.asyncio
async def test_async_client_is_ready() -> None:
    async with weaviate.use_async_with_weaviate_cloud(
        cluster_url=WCS_URL, auth_credentials=WCS_CREDS, skip_init_checks=True
    ) as client:
        assert await client.is_ready()


def test_local_proxies() -> None:
    with weaviate.connect_to_local(
        additional_config=wvc.init.AdditionalConfig(
            proxies=wvc.init.Proxies(
                http="http://localhost:8075",
                grpc="http://localhost:10000",
            )
        )
    ) as client:
        client.collections.delete("TestLocalProxies")
        collection = client.collections.create(
            "TestLocalProxies",
            properties=[wvc.config.Property(name="name", data_type=wvc.config.DataType.TEXT)],
            vectorizer_config=Configure.Vectorizer.none(),
        )
        collection.data.insert({"name": "Test"})
        assert collection.query.fetch_objects().objects[0].properties["name"] == "Test"


@pytest.mark.asyncio
async def test_async_client_inside_sync_client(caplog: pytest.LogCaptureFixture) -> None:
    with weaviate.connect_to_local() as client:
        async with weaviate.use_async_with_local() as aclient:
            assert client.is_ready()
            assert await aclient.is_ready()
            assert "BlockingIOError: [Errno 35] Resource temporarily unavailable" not in caplog.text


@pytest.mark.asyncio
async def test_sync_client_inside_async_client(caplog: pytest.LogCaptureFixture) -> None:
    async with weaviate.use_async_with_local() as aclient:
        with weaviate.connect_to_local() as client:
            assert client.is_ready()
            assert await aclient.is_ready()
            assert "BlockingIOError: [Errno 35] Resource temporarily unavailable" not in caplog.text
