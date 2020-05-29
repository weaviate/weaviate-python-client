import unittest
from weaviate.util import is_weaviate_thing_url, get_uuid_from_weaviate_url, _is_sub_schema

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

    def test_is_sub_schema(self):
        self.assertTrue(_is_sub_schema(schema_set, schema_set))
        self.assertTrue(_is_sub_schema(schema_sub_set, schema_set))
        self.assertTrue(_is_sub_schema({}, schema_set))
        self.assertFalse(_is_sub_schema(disjoint_set, schema_set))
        self.assertFalse(_is_sub_schema(partial_set, schema_set))


schema_set = {
    "actions": {
        "classes": [
            {
                "class": "Ollie",
                "properties": [{"name": "height"}]
            },
            {
                "class": "Shuvit",
                "properties": [{"name": "direction"}]
            }
        ],
        "type": "action"
    },
    "things": {
        "classes": [
            {
                "class": "Board",
                "properties": [{"name": "brand"},
                               {"name": "art"},
                               {"name": "size"}]
            },
            {
                "class": "Truck",
                "properties": [{"name": "name"},
                               {"name": "height"}]
            }
        ],
    }
}

schema_sub_set = {
    "actions": {
        "classes": [
            {
                "class": "Ollie",
                "properties": [{"name": "height"}]
            }
        ],
        "type": "action"
    },
    "things": {
        "classes": [
            {
                "class": "Board",
                "properties": [{"name": "brand"},
                               {"name": "art"},
                               {"name": "size"}]
            }
        ],
    }
}

disjoint_set = {
    "actions": {
        "classes": [
            {
                "class": "Manual",
                "properties": [{"name": "nose"}]
            }
        ],
        "type": "action"
    },
    "things": {
        "classes": [
            {
                "class": "Bearings",
                "properties": [{"name": "brand"}]
            }
        ],
    }
}

partial_set = {
    "actions": {
        "classes": [
            {
                "class": "Ollie",
                "properties": [{"name": "height"}]
            },
            {
                "class": "Shuvit",
                "properties": [{"name": "direction"}]
            },
            {
                "class": "Manual",
                "properties": [{"name": "nose"}]
            }
        ],
        "type": "action"
    },
    "things": {
        "classes": [
            {
                "class": "Board",
                "properties": [{"name": "brand"},
                               {"name": "art"},
                               {"name": "size"}]
            },
            {
                "class": "Truck",
                "properties": [{"name": "name"},
                               {"name": "height"}]
            },
            {
                "class": "Bearings",
                "properties": [{"name": "brand"}]
            }
        ],
    }
}