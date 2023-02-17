import unittest
from unittest.mock import patch
import pathlib


from weaviate import embedded
from weaviate.embedded import EmbeddedDB
from weaviate.exceptions import WeaviateStartUpError
from weaviate.util import is_port_available


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
        file.unlink(missing_ok=True)
        self.embedded_db.stop()

    def test_end_to_end(self):
        self.embedded_db = embedded_db = EmbeddedDB(url="embedded")
        self.assertTrue(is_port_available(embedded_db.port))
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
            mocked_print.assert_called_once_with("weaviate is already running")
