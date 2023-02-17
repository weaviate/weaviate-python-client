import unittest

from weaviate.embedded import EmbeddedDB, Singleton


class TestWeaviateClient(unittest.TestCase):

    def tearDown(self) -> None:
        Singleton.clear()

    def test__init__(self):
        self.assertEqual(EmbeddedDB(url="embedded").port, 6666)

        # should still be 6666 since it's a singleton
        embedded_db = EmbeddedDB(url="embedded?port=30666")
        self.assertEqual(embedded_db.port, 6666)

    def test__init__non_default(self):
        self.assertEqual(EmbeddedDB(url="embedded?port=30666").port, 30666)

        # should still be 6666 since it's a singleton
        embedded_db = EmbeddedDB(url="embedded")
        self.assertEqual(embedded_db.port, 30666)
