import os
import signal
import socket
import tarfile
import time
from pathlib import Path
from sys import platform
from unittest.mock import patch

import pytest
import requests
import uuid
from pytest_httpserver import HTTPServer
from werkzeug import Request, Response

import weaviate
from weaviate import embedded
from weaviate.embedded import EmbeddedDB, EmbeddedOptions
from weaviate.exceptions import WeaviateEmbeddedInvalidVersionError, WeaviateStartUpError

if platform != "linux" and platform != "darwin":
    pytest.skip("Currently only supported on linux", allow_module_level=True)


def test_embedded__init__(tmp_path):
    assert (
        EmbeddedDB(EmbeddedOptions(port=8079, persistence_data_path=tmp_path)).options.port == 8079
    )


def test_embedded__init__non_default_port(tmp_path):
    assert (
        EmbeddedDB(EmbeddedOptions(port=30666, persistence_data_path=tmp_path)).options.port
        == 30666
    )


def test_embedded_ensure_binary_exists(tmp_path):
    bin_path = tmp_path / "notcreated-yet/bin/weaviate-embedded"
    assert bin_path.is_file, False
    embedded_db = EmbeddedDB(
        EmbeddedOptions(binary_path=str(bin_path), persistence_data_path=tmp_path / "2")
    )
    embedded_db.ensure_weaviate_binary_exists()
    assert Path(embedded_db.options.binary_path).is_file, True


def test_version_parsing(tmp_path):
    bin_path = tmp_path / "bin"
    embedded_db = EmbeddedDB(
        EmbeddedOptions(
            binary_path=str(bin_path),
            version="https://github.com/weaviate/weaviate/releases/download/v1.18.1/weaviate-v1.18.1-linux-amd64.tar.gz",
            persistence_data_path=tmp_path / "2",
        )
    )
    embedded_db.ensure_weaviate_binary_exists()
    embedded_file_name = list(bin_path.iterdir())
    assert len(embedded_file_name) == 1  # .tgz file was deleted
    assert "v1.18.1" in str(embedded_file_name[0])


def test_download_no_version_parsing(httpserver: HTTPServer, tmp_path):
    """Test downloading weaviate from a non-github url."""

    def handler(request: Request):
        with open(Path(tmp_path, "weaviate"), "w") as _:
            with tarfile.open(Path(tmp_path, "tmp_weaviate.tar.gz"), "w:gz") as tar:
                tar.add(Path(tmp_path, "weaviate"), arcname="weaviate")

        return Response(open(Path(tmp_path, "tmp_weaviate.tar.gz"), mode="rb"))

    httpserver.expect_request("/tmp_weaviate.tar.gz").respond_with_handler(handler)

    bin_path = tmp_path / "bin"
    embedded_db = EmbeddedDB(
        EmbeddedOptions(
            binary_path=str(bin_path),
            version=httpserver.url_for("/tmp_weaviate.tar.gz"),
            persistence_data_path=tmp_path / "2",
        )
    )
    embedded_db.ensure_weaviate_binary_exists()
    embedded_file_name = list(bin_path.iterdir())
    assert len(embedded_file_name) == 1  # .tgz file was deleted


def test_embedded_ensure_binary_exists_same_as_tar_binary_name(tmp_path):
    bin_path = tmp_path / "notcreated-yet/bin/weaviate"
    assert bin_path.is_file, False
    embedded_db = EmbeddedDB(
        EmbeddedOptions(binary_path=str(bin_path), persistence_data_path=tmp_path)
    )
    embedded_db.ensure_weaviate_binary_exists()
    assert Path(embedded_db.options.binary_path).is_file, True


@pytest.fixture(scope="session")
def embedded_db_binary_path(tmp_path_factory: pytest.TempPathFactory):
    embedded.weaviate_binary_path = (
        tmp_path_factory.mktemp("embedded-test") / "weaviate-embedded-binary"
    )


@pytest.mark.parametrize(
    "options", [EmbeddedOptions(), EmbeddedOptions(port=30666, grpc_port=50046)]
)
def test_embedded_end_to_end(options: EmbeddedDB, tmp_path):
    options.binary_path = tmp_path
    options.persistence_data_path = tmp_path
    embedded_db = EmbeddedDB(options=options)
    assert embedded_db.is_listening() is False
    with pytest.raises(WeaviateStartUpError):
        with patch("time.sleep") as mocked_sleep:
            embedded_db.wait_till_listening()
            mocked_sleep.assert_has_calls([0.1] * 300)

    embedded_db.ensure_running()
    assert embedded_db.is_listening() is True
    with patch("builtins.print") as mocked_print:
        embedded_db.start()
        mocked_print.assert_called_once_with(
            f"embedded weaviate is already listening on port {options.port}"
        )

    # killing the process should restart it again when ensure running is called
    os.kill(embedded_db.process.pid, signal.SIGTERM)
    time.sleep(0.2)
    assert embedded_db.is_listening() is False
    embedded_db.ensure_running()
    assert embedded_db.is_listening() is True
    embedded_db.stop()


def test_embedded_multiple_instances(tmp_path_factory: pytest.TempPathFactory):
    embedded_db = EmbeddedDB(
        EmbeddedOptions(
            port=30662,
            persistence_data_path=tmp_path_factory.mktemp("data"),
            binary_path=tmp_path_factory.mktemp("bin"),
            additional_env_vars={"GRPC_PORT": "50053"},
            grpc_port=50053,
        )
    )
    embedded_db2 = EmbeddedDB(
        EmbeddedOptions(
            port=30663,
            persistence_data_path=tmp_path_factory.mktemp("data"),
            binary_path=tmp_path_factory.mktemp("bin"),
            additional_env_vars={"GRPC_PORT": "50054"},
            grpc_port=50054,
        )
    )
    embedded_db.ensure_running()
    assert embedded_db.is_listening() is True
    embedded_db2.ensure_running()
    assert embedded_db2.is_listening() is True


def test_embedded_different_versions(tmp_path_factory: pytest.TempPathFactory):
    client1 = weaviate.Client(
        embedded_options=EmbeddedOptions(
            port=30664,
            persistence_data_path=tmp_path_factory.mktemp("data"),
            binary_path=tmp_path_factory.mktemp("bin"),
            version="https://github.com/weaviate/weaviate/releases/download/v1.18.1/weaviate-v1.18.1-linux-amd64.tar.gz",
        )
    )
    client2 = weaviate.Client(
        embedded_options=EmbeddedOptions(
            port=30665,
            persistence_data_path=tmp_path_factory.mktemp("data"),
            binary_path=tmp_path_factory.mktemp("bin"),
            version="https://github.com/weaviate/weaviate/releases/download/v1.18.0/weaviate-v1.18.0-linux-amd64.tar.gz",
        )
    )
    meta1 = client1.get_meta()
    assert meta1["version"] == "1.18.1"
    meta2 = client2.get_meta()
    assert meta2["version"] == "1.18.0"


def test_custom_env_vars(tmp_path_factory: pytest.TempPathFactory):
    client = weaviate.Client(
        embedded_options=EmbeddedOptions(
            binary_path=tmp_path_factory.mktemp("bin"),
            additional_env_vars={"ENABLE_MODULES": "", "GRPC_PORT": "50057"},
            persistence_data_path=tmp_path_factory.mktemp("data"),
            port=30666,
        )
    )
    meta = client.get_meta()
    assert len(meta["modules"]) == 0


def test_weaviate_state(tmp_path_factory: pytest.TempPathFactory) -> None:
    """Test that weaviate keeps the state between different runs."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    port = 36545
    data_path = tmp_path_factory.mktemp("data")
    client = weaviate.Client(
        embedded_options=EmbeddedOptions(
            binary_path=tmp_path_factory.mktemp("bin"),
            port=port,
            persistence_data_path=data_path,
            additional_env_vars={"GRPC_PORT": "50058"},
            grpc_port=50058,
        ),
    )
    client.data_object.create({"name": "Name"}, "Person", uuid.uuid4())
    assert sock.connect_ex(("127.0.0.1", port)) == 0  # running

    client._connection.embedded_db.stop()
    del client
    time.sleep(5)  # give weaviate time to shut down

    assert sock.connect_ex(("127.0.0.1", port)) != 0  # not running anymore

    client = weaviate.Client(
        embedded_options=EmbeddedOptions(
            binary_path=tmp_path_factory.mktemp("bin"),
            port=port,
            persistence_data_path=data_path,
            additional_env_vars={"GRPC_PORT": "50059"},
            grpc_port=50059,
        )
    )
    count = client.query.aggregate("Person").with_meta_count().do()
    assert count["data"]["Aggregate"]["Person"][0]["meta"]["count"] == 1


def test_version(tmp_path_factory: pytest.TempPathFactory):
    client = weaviate.Client(
        embedded_options=EmbeddedOptions(
            persistence_data_path=tmp_path_factory.mktemp("data"),
            binary_path=tmp_path_factory.mktemp("bin"),
            version="1.18.2",
            port=30667,
        )
    )
    meta = client.get_meta()
    assert meta["version"] == "1.18.2"


def test_latest(tmp_path_factory: pytest.TempPathFactory):
    client = weaviate.Client(
        embedded_options=EmbeddedOptions(
            persistence_data_path=tmp_path_factory.mktemp("data"),
            binary_path=tmp_path_factory.mktemp("bin"),
            version="latest",
            port=30668,
            additional_env_vars={"GRPC_PORT": "50060"},
            grpc_port=50060,
        )
    )
    meta = client.get_meta()
    latest = requests.get("https://api.github.com/repos/weaviate/weaviate/releases/latest").json()
    assert "v" + meta["version"] == latest["tag_name"]


@pytest.mark.parametrize(
    "version",
    [
        "v1.16.6",
        "sdgfsdfposdfjpsdf",
        "httttp://github.com/weaviate/weaviate/releases/download/v1.18.0/weaviate-v1.18.0-linux-amd64.tar.gz",
        "https://github.com/weaviate/weaviate/releases/download/v1.18.0/weaviate-v1.18.0-linux-amd64.tar",
    ],
)
def test_invalid_version(tmp_path_factory: pytest.TempPathFactory, version):
    with pytest.raises(WeaviateEmbeddedInvalidVersionError):
        weaviate.Client(
            embedded_options=EmbeddedOptions(
                persistence_data_path=tmp_path_factory.mktemp("data"),
                binary_path=tmp_path_factory.mktemp("bin"),
                version=version,
            )
        )


def test_embedded_with_grpc_port(tmp_path_factory: pytest.TempPathFactory):
    client = weaviate.Client(
        embedded_options=EmbeddedOptions(
            persistence_data_path=tmp_path_factory.mktemp("data"),
            binary_path=tmp_path_factory.mktemp("bin"),
            version="latest",
            port=30668,
            grpc_port=50061,
        ),
    )

    assert client.is_ready()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1.0)  # we're only pinging the port, 1s is plenty

    assert sock.connect_ex(("127.0.0.1", 50061)) == 0  # running


def test_embedded_with_grpc_port_default(tmp_path_factory: pytest.TempPathFactory):
    client = weaviate.Client(
        embedded_options=EmbeddedOptions(
            persistence_data_path=tmp_path_factory.mktemp("data"),
            binary_path=tmp_path_factory.mktemp("bin"),
            version="latest",
            port=30669,
        )
    )

    assert client.is_ready()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1.0)  # we're only pinging the port, 1s is plenty

    assert sock.connect_ex(("127.0.0.1", 50060)) == 0  # running


def test_embedded_stop(tmp_path_factory: pytest.TempPathFactory):
    client = weaviate.Client(
        embedded_options=EmbeddedOptions(
            persistence_data_path=tmp_path_factory.mktemp("data"),
            binary_path=tmp_path_factory.mktemp("bin"),
            version="latest",
            port=30668,
            grpc_port=50061,
        ),
    )

    assert client.is_ready()

    assert client._connection.embedded_db.process is not None
    client._connection.embedded_db.stop()
    assert client._connection.embedded_db.process is None
    client._connection.embedded_db.stop()
    assert client._connection.embedded_db.process is None
