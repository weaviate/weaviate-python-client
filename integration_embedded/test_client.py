import pytest
from typing import Tuple, Union

import weaviate
from weaviate.classes.init import AdditionalConfig, Timeout
from weaviate.embedded import WEAVIATE_VERSION
from weaviate.exceptions import WeaviateClosedClientError


@pytest.mark.parametrize("timeout", [(1, 2), Timeout(query=1, insert=2, init=2)])
def test_client_with_extra_options(
    timeout: Union[Tuple[int, int], Timeout], tmp_path_factory: pytest.TempPathFactory
) -> None:
    additional_config = AdditionalConfig(timeout=timeout, trust_env=True)
    client = weaviate.connect_to_embedded(
        port=8070,
        grpc_port=50040,
        additional_config=additional_config,
        environment_variables={"DISABLE_TELEMETRY": "true"},
        persistence_data_path=tmp_path_factory.mktemp("data"),
        binary_path=tmp_path_factory.mktemp("bin"),
    )
    try:
        assert client._connection.timeout_config == Timeout(query=1, insert=2, init=2)
    finally:
        client.close()


def test_connect_and_close_to_embedded(tmp_path_factory: pytest.TempPathFactory) -> None:
    # Can't use the default port values as they are already in use by the local instances
    client = weaviate.connect_to_embedded(
        port=30668,
        grpc_port=50151,
        environment_variables={"DISABLE_TELEMETRY": "true"},
        persistence_data_path=tmp_path_factory.mktemp("data"),
        binary_path=tmp_path_factory.mktemp("bin"),
    )
    try:
        assert client.is_connected()
        metadata = client.get_meta()
        assert WEAVIATE_VERSION == metadata["version"]
        assert client.is_ready()
        assert "30668" == metadata["hostname"].split(":")[2]
        assert client.is_live()

        client.close()
        assert not client.is_connected()
        with pytest.raises(WeaviateClosedClientError):
            client.get_meta()
    finally:
        client.close()


def test_embedded_as_context_manager(tmp_path_factory: pytest.TempPathFactory) -> None:
    with weaviate.connect_to_embedded(
        port=30668,
        grpc_port=50152,
        environment_variables={"DISABLE_TELEMETRY": "true"},
        persistence_data_path=tmp_path_factory.mktemp("data"),
        binary_path=tmp_path_factory.mktemp("bin"),
    ) as client:
        assert client.is_connected()
        metadata = client.get_meta()
        assert WEAVIATE_VERSION == metadata["version"]
        assert client.is_ready()
        assert client.is_live()

    assert not client.is_connected()
    with pytest.raises(WeaviateClosedClientError):
        client.get_meta()


@pytest.mark.asyncio
async def test_embedded_with_async_as_context_manager(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    async with weaviate.use_async_with_embedded(
        port=8076,
        grpc_port=50153,
        environment_variables={"DISABLE_TELEMETRY": "true"},
        persistence_data_path=tmp_path_factory.mktemp("data"),
        binary_path=tmp_path_factory.mktemp("bin"),
    ) as client:
        assert client.is_connected()
        metadata = await client.get_meta()
        assert WEAVIATE_VERSION == metadata["version"]
        assert client.is_ready()
        assert client.is_live()

    assert not client.is_connected()
    with pytest.raises(WeaviateClosedClientError):
        await client.get_meta()


def test_embedded_with_wrong_version(tmp_path_factory: pytest.TempPathFactory) -> None:
    with pytest.raises(weaviate.exceptions.WeaviateEmbeddedInvalidVersionError):
        weaviate.connect_to_embedded(
            version="this_version_does_not_exist",
            environment_variables={"DISABLE_TELEMETRY": "true"},
            persistence_data_path=tmp_path_factory.mktemp("data"),
            binary_path=tmp_path_factory.mktemp("bin"),
        )


def test_embedded_already_running(tmp_path_factory: pytest.TempPathFactory) -> None:
    client = weaviate.connect_to_embedded(
        port=8096,
        grpc_port=50155,
        environment_variables={"DISABLE_TELEMETRY": "true"},
        persistence_data_path=tmp_path_factory.mktemp("data"),
        binary_path=tmp_path_factory.mktemp("bin"),
    )
    try:
        assert client._connection.embedded_db is not None
        assert client._connection.embedded_db.process is not None

        with pytest.raises(weaviate.exceptions.WeaviateStartUpError):
            weaviate.connect_to_embedded(
                port=8096, grpc_port=50155, environment_variables={"DISABLE_TELEMETRY": "true"}
            )
    finally:
        client.close()


def test_embedded_startup_with_blocked_http_port(tmp_path_factory: pytest.TempPathFactory) -> None:
    client = weaviate.connect_to_embedded(
        port=8098,
        grpc_port=50096,
        environment_variables={"DISABLE_TELEMETRY": "true"},
        persistence_data_path=tmp_path_factory.mktemp("data"),
        binary_path=tmp_path_factory.mktemp("bin"),
    )
    try:
        with pytest.raises(weaviate.exceptions.WeaviateStartUpError):
            weaviate.connect_to_embedded(
                port=8098,
                grpc_port=50097,
                environment_variables={"DISABLE_TELEMETRY": "true"},
                persistence_data_path=tmp_path_factory.mktemp("data"),
                binary_path=tmp_path_factory.mktemp("bin"),
            )
    finally:
        client.close()


def test_embedded_startup_with_blocked_grpc_port(tmp_path_factory: pytest.TempPathFactory) -> None:
    client = weaviate.connect_to_embedded(
        port=8099,
        grpc_port=50150,
        environment_variables={"DISABLE_TELEMETRY": "true"},
        persistence_data_path=tmp_path_factory.mktemp("data"),
        binary_path=tmp_path_factory.mktemp("bin"),
    )
    try:
        with pytest.raises(weaviate.exceptions.WeaviateStartUpError):
            weaviate.connect_to_embedded(
                port=8100, grpc_port=50150, environment_variables={"DISABLE_TELEMETRY": "true"}
            )
    finally:
        client.close()
