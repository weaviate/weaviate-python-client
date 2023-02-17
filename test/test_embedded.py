import unittest
from unittest.mock import patch
import pathlib


from weaviate import embedded
from weaviate.embedded import EmbeddedDB
from weaviate.exceptions import WeaviateStartUpError


class TestWeaviateClient(unittest.TestCase):

    def setUp(self) -> None:
        embedded.weaviate_binary_path = "./weaviate-embedded-unitests-delete-me"

    def tearDown(self) -> None:
        file = pathlib.Path(embedded.weaviate_binary_path)
        file.unlink(missing_ok=True)

    def test__init__(self):
        self.assertEqual(EmbeddedDB(url="embedded").port, 6666)

    def test__init__non_default_port(self):
        self.assertEqual(EmbeddedDB(url="embedded?port=30666").port, 30666)

    def test_end_to_end(self):
        embedded_db = EmbeddedDB(url="embedded")
        self.assertFalse(embedded_db.is_running())
        self.assertFalse(embedded_db.is_listening())
        with self.assertRaises(WeaviateStartUpError):
            with patch("time.sleep") as mocked_sleep:
                embedded_db.wait_till_listening()
                mocked_sleep.assert_has_calls([0.1] * 3000)

        embedded_db.ensure_running()
        self.assertTrue(embedded_db.is_running())
        self.assertTrue(embedded_db.is_listening())
