from pathlib import Path
import pytest
import time
import os
import signal
from unittest.mock import patch

from weaviate import embedded
from weaviate.embedded import EmbeddedDB, EmbeddedOptions
from weaviate.exceptions import WeaviateStartUpError


def test_embedded__init__():
    assert EmbeddedDB(EmbeddedOptions(port=6666)).port == 6666


def test_embedded__init__non_default_port():
    assert EmbeddedDB(EmbeddedOptions(port=30666)).port == 30666


def test_embedded_ensure_binary_exists(tmp_path):
    bin_path = tmp_path / "notcreated-yet/bin/weaviate-embedded"
    assert bin_path.is_file, False
    embedded_db = EmbeddedDB(EmbeddedOptions(binary_path=str(bin_path)))
    embedded_db.ensure_weaviate_binary_exists()
    assert Path(embedded_db.options.binary_path).is_file, True


def test_embedded_ensure_binary_exists_same_as_tar_binary_name(tmp_path):
    bin_path = tmp_path / "notcreated-yet/bin/weaviate"
    assert bin_path.is_file, False
    embedded_db = EmbeddedDB(EmbeddedOptions(binary_path=str(bin_path)))
    embedded_db.ensure_weaviate_binary_exists()
    assert Path(embedded_db.options.binary_path).is_file, True


@pytest.fixture(scope="session")
def embedded_db_binary_path(tmp_path_factory):
    embedded.weaviate_binary_path = (
        tmp_path_factory.mktemp("embedded-test") / "weaviate-embedded-binary"
    )


@pytest.mark.parametrize("options", [EmbeddedOptions(), EmbeddedOptions(port=30666)])
def test_embedded_end_to_end(options, embedded_db_binary_path):
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
            f"embedded weaviate is already listing on port {options.port}"
        )

    # killing the process should restart it again when ensure running is called
    os.kill(embedded_db.pid, signal.SIGTERM)
    time.sleep(0.2)
    assert embedded_db.is_listening() is False
    embedded_db.ensure_running()
    assert embedded_db.is_listening() is True
    embedded_db.stop()


def test_embedded_multiple_instances(embedded_db_binary_path, tmp_path):
    embedded_db = EmbeddedDB(
        EmbeddedOptions(
            cluster_hostname="db1", port=30664, persistence_data_path=(tmp_path / "db1").absolute()
        )
    )
    embedded_db2 = EmbeddedDB(
        EmbeddedOptions(
            cluster_hostname="db2", port=30665, persistence_data_path=(tmp_path / "db2").absolute()
        )
    )
    embedded_db.ensure_running()
    assert embedded_db.is_listening() is True
    embedded_db2.ensure_running()
    assert embedded_db2.is_listening() is True
