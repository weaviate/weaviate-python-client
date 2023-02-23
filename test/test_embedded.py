import pytest
import time
import os
import signal
from unittest.mock import patch

from weaviate import embedded
from weaviate.embedded import EmbeddedDB
from weaviate.exceptions import WeaviateStartUpError


def test_embedded__init__():
    assert EmbeddedDB(url="embedded").port == 6666


def test_embedded__init__non_default_port():
    assert EmbeddedDB(url="embedded?port=30666").port == 30666


@pytest.fixture(scope="session")
def embedded_db_binary_path(tmp_path_factory):
    embedded.weaviate_binary_path = (
        tmp_path_factory.mktemp("embedded-test") / "weaviate-embedded-binary"
    )


@pytest.mark.parametrize("url", ["embedded", "embedded?port=30666"])
def test_embedded_end_to_end(url, embedded_db_binary_path):
    embedded_db = EmbeddedDB(url=url)
    assert embedded_db.is_running() is False
    assert embedded_db.is_listening() is False
    with pytest.raises(WeaviateStartUpError):
        with patch("time.sleep") as mocked_sleep:
            embedded_db.wait_till_listening()
            mocked_sleep.assert_has_calls([0.1] * 3000)

    embedded_db.ensure_running()
    assert embedded_db.is_running() is True
    assert embedded_db.is_listening() is True
    with patch("builtins.print") as mocked_print:
        embedded_db.start()
        mocked_print.assert_called_once_with("embedded weaviate is already running")

    # killing the process should restart it again when ensure running is called
    os.kill(embedded_db.pid, signal.SIGTERM)
    time.sleep(0.2)
    assert embedded_db.is_running() is False
    assert embedded_db.is_listening() is False
    embedded_db.ensure_running()
    assert embedded_db.is_running() is True
    assert embedded_db.is_listening() is True
    embedded_db.stop()
