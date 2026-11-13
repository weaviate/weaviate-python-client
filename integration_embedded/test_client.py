from contextlib import ExitStack
from typing import List, Tuple, Union

import pytest

import weaviate
from weaviate.classes.init import AdditionalConfig, Timeout
from weaviate.embedded import WEAVIATE_VERSION, _hold_port
from weaviate.exceptions import WeaviateClosedClientError


def _free_ports(count: int) -> List[int]:
    """Return `count` distinct ports that were free when chosen.

    Fixed ports can already be held by another socket on a CI runner, which makes Weaviate exit
    at startup.
    """
    with ExitStack() as held:
        return [_hold_port(held) for _ in range(count)]


@pytest.mark.parametrize("timeout", [(1, 2), Timeout(query=1, insert=2, init=2)])
def test_client_with_extra_options(
    timeout: Union[Tuple[int, int], Timeout], tmp_path_factory: pytest.TempPathFactory
) -> None:
    additional_config = AdditionalConfig(timeout=timeout, trust_env=True)
    port, grpc_port = _free_ports(2)
    client = weaviate.connect_to_embedded(
        port=port,
        grpc_port=grpc_port,
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
    port, grpc_port = _free_ports(2)
    client = weaviate.connect_to_embedded(
        port=port,
        grpc_port=grpc_port,
        environment_variables={"DISABLE_TELEMETRY": "true"},
        persistence_data_path=tmp_path_factory.mktemp("data"),
        binary_path=tmp_path_factory.mktemp("bin"),
    )
    try:
        assert client.is_connected()
        metadata = client.get_meta()
        assert WEAVIATE_VERSION == metadata["version"]
        assert client.is_ready()
        assert str(port) == metadata["hostname"].split(":")[2]
        assert client.is_live()

        client.close()
        assert not client.is_connected()
        with pytest.raises(WeaviateClosedClientError):
            client.get_meta()
    finally:
        client.close()


def test_embedded_as_context_manager(tmp_path_factory: pytest.TempPathFactory) -> None:
    port, grpc_port = _free_ports(2)
    with weaviate.connect_to_embedded(
        port=port,
        grpc_port=grpc_port,
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
    port, grpc_port = _free_ports(2)
    async with weaviate.use_async_with_embedded(
        port=port,
        grpc_port=grpc_port,
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
    port, grpc_port = _free_ports(2)
    client = weaviate.connect_to_embedded(
        port=port,
        grpc_port=grpc_port,
        environment_variables={"DISABLE_TELEMETRY": "true"},
        persistence_data_path=tmp_path_factory.mktemp("data"),
        binary_path=tmp_path_factory.mktemp("bin"),
    )
    try:
        assert client._connection.embedded_db is not None
        assert client._connection.embedded_db.process is not None

        with pytest.raises(weaviate.exceptions.WeaviateStartUpError):
            weaviate.connect_to_embedded(
                port=port, grpc_port=grpc_port, environment_variables={"DISABLE_TELEMETRY": "true"}
            )
    finally:
        client.close()


def test_embedded_startup_with_blocked_http_port(tmp_path_factory: pytest.TempPathFactory) -> None:
    port, grpc_port, other_grpc_port = _free_ports(3)
    client = weaviate.connect_to_embedded(
        port=port,
        grpc_port=grpc_port,
        environment_variables={"DISABLE_TELEMETRY": "true"},
        persistence_data_path=tmp_path_factory.mktemp("data"),
        binary_path=tmp_path_factory.mktemp("bin"),
    )
    try:
        with pytest.raises(weaviate.exceptions.WeaviateStartUpError):
            weaviate.connect_to_embedded(
                port=port,
                grpc_port=other_grpc_port,
                environment_variables={"DISABLE_TELEMETRY": "true"},
                persistence_data_path=tmp_path_factory.mktemp("data"),
                binary_path=tmp_path_factory.mktemp("bin"),
            )
    finally:
        client.close()


def test_embedded_startup_with_blocked_grpc_port(tmp_path_factory: pytest.TempPathFactory) -> None:
    port, other_port, grpc_port = _free_ports(3)
    client = weaviate.connect_to_embedded(
        port=port,
        grpc_port=grpc_port,
        environment_variables={"DISABLE_TELEMETRY": "true"},
        persistence_data_path=tmp_path_factory.mktemp("data"),
        binary_path=tmp_path_factory.mktemp("bin"),
    )
    try:
        with pytest.raises(weaviate.exceptions.WeaviateStartUpError):
            weaviate.connect_to_embedded(
                port=other_port,
                grpc_port=grpc_port,
                environment_variables={"DISABLE_TELEMETRY": "true"},
            )
    finally:
        client.close()


def test_embedded_startup_with_data_from_other_port(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    data_path = tmp_path_factory.mktemp("data")
    binary_path = tmp_path_factory.mktemp("bin")
    client = weaviate.connect_to_embedded(
        port=8180,
        grpc_port=50180,
        environment_variables={"DISABLE_TELEMETRY": "true"},
        persistence_data_path=data_path,
        binary_path=binary_path,
    )
    client.close()

    # The Raft state saved on port 8180 does not list the node on port 8181 as a voter,
    # so the new node never elects a leader and the readiness check times out.
    with pytest.raises(weaviate.exceptions.WeaviateStartUpError, match="persistence_data_path"):
        weaviate.connect_to_embedded(
            port=8181,
            grpc_port=50181,
            environment_variables={"DISABLE_TELEMETRY": "true"},
            persistence_data_path=data_path,
            binary_path=binary_path,
        )


def test_embedded_create_restore_backup(tmp_path_factory: pytest.TempPathFactory) -> None:
    num_objects = 10
    collection_name = "BackedUp"
    backup_id = "backup0"

    port, grpc_port = _free_ports(2)
    client = weaviate.connect_to_embedded(
        persistence_data_path=tmp_path_factory.mktemp("data"),
        port=port,
        grpc_port=grpc_port,
        environment_variables={
            "ENABLE_MODULES": "backup-filesystem",
            "BACKUP_FILESYSTEM_PATH": tmp_path_factory.mktemp("backup"),
            "DISABLE_TELEMETRY": "true",
        },
        version="latest",
    )

    try:
        col = client.collections.create(collection_name)
        with col.batch.dynamic() as batch:
            for i in range(num_objects):
                batch.add_object(properties={"text": f"text-{i}"})
        assert len(col) == num_objects

        col.backup.create(backup_id=backup_id, backend="filesystem", wait_for_completion=True)
        client.collections.delete(collection_name)
        col.backup.restore(backup_id=backup_id, backend="filesystem", wait_for_completion=True)

        assert len(col) == num_objects
        client.collections.delete(collection_name)
    finally:
        client.close()
