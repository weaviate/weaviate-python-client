import unittest
from weaviate.util import is_weaviate_thing_url, get_uuid_from_weaviate_url

class TestWeaviateClient(unittest.TestCase):
    def test_is_weaviate_thing_url(self):

        self.assertTrue(
            is_weaviate_thing_url("weaviate://localhost/things/28f3f61b-b524-45e0-9bbe-2c1550bf73d2"))
        self.assertTrue(
            is_weaviate_thing_url("weaviate://some-domain.com/things/28f3f61b-b524-45e0-9bbe-2c1550bf73d2"))
        self.assertTrue(
            is_weaviate_thing_url("weaviate://localhost/actions/28f3f61b-b524-45e0-9bbe-2c1550bf73d2"))
        self.assertFalse(
            is_weaviate_thing_url("http://some-domain.com/things/28f3f61b-b524-45e0-9bbe-2c1550bf73d2"))
        self.assertFalse(
            is_weaviate_thing_url("weaviate://localhost/nachos/28f3f61b-b524-45e0-9bbe-2c1550bf73d2"))
        self.assertFalse(
            is_weaviate_thing_url("weaviate://localhost/things/f61b-b524-45e0-9bbe-2c1550bf73d2"))

    def test_get_uuid_from_weaviate_url(self):
        self.assertEqual("28f3f61b-b524-45e0-9bbe-2c1550bf73d2",
                         get_uuid_from_weaviate_url(
                             "weaviate://localhost/things/28f3f61b-b524-45e0-9bbe-2c1550bf73d2"))
