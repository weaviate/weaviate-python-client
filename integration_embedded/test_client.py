import pytest
from typing import Tuple, Union

import weaviate
from weaviate.classes.init import AdditionalConfig, Timeout
from weaviate.exceptions import WeaviateClosedClientError


@pytest.mark.parametrize("timeout", [(1, 2), Timeout(query=1, insert=2, init=2)])
def test_client_with_extra_options(timeout: Union[Tuple[int, int], Timeout]) -> None:
    additional_config = AdditionalConfig(timeout=timeout, trust_env=True)
    client = weaviate.connect_to_embedded(
        port=8070,
        grpc_port=50040,
        additional_config=additional_config,
        environment_variables={"DISABLE_TELEMETRY": "true"},
    )
    try:
        assert client._connection.timeout_config == Timeout(query=1, insert=2, init=2)
    finally:
        client.close()


def test_connect_and_close_to_embedded() -> None:
    # Can't use the default port values as they are already in use by the local instances
    client = weaviate.connect_to_embedded(
        port=8078, grpc_port=50151, environment_variables={"DISABLE_TELEMETRY": "true"}
    )
    try:
        assert client.is_connected()
        metadata = client.get_meta()
        assert "1.23.7" == metadata["version"]
        assert client.is_ready()
        assert "8078" == metadata["hostname"].split(":")[2]
        assert client.is_live()

        client.close()
        assert not client.is_connected()
        with pytest.raises(WeaviateClosedClientError):
            client.get_meta()
    finally:
        client.close()


def test_embedded_as_context_manager() -> None:
    default_version = "1.23.7"
    with weaviate.connect_to_embedded(
        port=8077, grpc_port=50152, environment_variables={"DISABLE_TELEMETRY": "true"}
    ) as client:
        assert client.is_connected()
        metadata = client.get_meta()
        assert default_version == metadata["version"]
        assert client.is_ready()
        assert client.is_live()

    assert not client.is_connected()
    with pytest.raises(WeaviateClosedClientError):
        client.get_meta()


def test_embedded_with_wrong_version() -> None:
    with pytest.raises(weaviate.exceptions.WeaviateEmbeddedInvalidVersionError):
        weaviate.connect_to_embedded(
            version="this_version_does_not_exist",
            environment_variables={"DISABLE_TELEMETRY": "true"},
        )


def test_embedded_already_running() -> None:
    client = weaviate.connect_to_embedded(
        port=8096, grpc_port=50155, environment_variables={"DISABLE_TELEMETRY": "true"}
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


def test_embedded_startup_with_blocked_http_port() -> None:
    client = weaviate.connect_to_embedded(
        port=8098, grpc_port=50096, environment_variables={"DISABLE_TELEMETRY": "true"}
    )
    try:
        with pytest.raises(weaviate.exceptions.WeaviateStartUpError):
            weaviate.connect_to_embedded(
                port=8098, grpc_port=50097, environment_variables={"DISABLE_TELEMETRY": "true"}
            )
    finally:
        client.close()


def test_embedded_startup_with_blocked_grpc_port() -> None:
    client = weaviate.connect_to_embedded(
        port=8099, grpc_port=50150, environment_variables={"DISABLE_TELEMETRY": "true"}
    )
    try:
        with pytest.raises(weaviate.exceptions.WeaviateStartUpError):
            weaviate.connect_to_embedded(
                port=8100, grpc_port=50150, environment_variables={"DISABLE_TELEMETRY": "true"}
            )
    finally:
        client.close()
