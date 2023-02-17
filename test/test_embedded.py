import unittest
import time
import os
import signal
from unittest.mock import patch
import pathlib

from weaviate import embedded
from weaviate.embedded import EmbeddedDB
from weaviate.exceptions import WeaviateStartUpError


class TestEmbeddedBasics(unittest.TestCase):
    def test__init__(self):
        self.assertEqual(EmbeddedDB(url="embedded").port, 6666)

    def test__init__non_default_port(self):
        self.assertEqual(EmbeddedDB(url="embedded?port=30666").port, 30666)


class TestEmbeddedEndToEnd(unittest.TestCase):
    def setUp(self) -> None:
        embedded.weaviate_binary_path = "./weaviate-embedded-unitests-delete-me"
        self.embedded_db: EmbeddedDB = None

    def tearDown(self) -> None:
        file = pathlib.Path(embedded.weaviate_binary_path)
        if file.exists():
            file.unlink()
        self.embedded_db.stop()

    def test_end_to_end_all(self):
        for url in ["embedded", "embedded?port=30666"]:
            print(f"Running test case for EmbeddedDB(url={url}")
            self.end_to_end_test(url)

    def end_to_end_test(self, url):
        self.embedded_db = embedded_db = EmbeddedDB(url=url)
        self.assertFalse(embedded_db.is_running())
        self.assertFalse(embedded_db.is_listening())
        with self.assertRaises(WeaviateStartUpError):
            with patch("time.sleep") as mocked_sleep:
                embedded_db.wait_till_listening()
                mocked_sleep.assert_has_calls([0.1] * 3000)

        embedded_db.ensure_running()
        self.assertTrue(embedded_db.is_running())
        self.assertTrue(embedded_db.is_listening())
        with patch("builtins.print") as mocked_print:
            embedded_db.start()
            mocked_print.assert_called_once_with("embedded weaviate is already running")

        # killing the process should restart it again when ensure running is called
        os.kill(embedded_db.pid, signal.SIGTERM)
        time.sleep(0.2)
        self.assertFalse(embedded_db.is_running())
        self.assertFalse(embedded_db.is_listening())
        embedded_db.ensure_running()
        self.assertTrue(embedded_db.is_running())
        self.assertTrue(embedded_db.is_listening())
