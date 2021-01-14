import unittest
from weaviate.util import is_weaviate_entity_url, get_uuid_from_weaviate_url, _is_sub_schema, is_object_url

class TestWeaviateClient(unittest.TestCase):

    def test_is_weaviate_thing_url(self):

        self.assertTrue(
            is_weaviate_entity_url("weaviate://localhost/things/28f3f61b-b524-45e0-9bbe-2c1550bf73d2"))
        self.assertTrue(
            is_weaviate_entity_url("weaviate://some-domain.com/things/28f3f61b-b524-45e0-9bbe-2c1550bf73d2"))
        self.assertTrue(
            is_weaviate_entity_url("weaviate://localhost/actions/28f3f61b-b524-45e0-9bbe-2c1550bf73d2"))
        self.assertFalse(
            is_weaviate_entity_url("http://some-domain.com/things/28f3f61b-b524-45e0-9bbe-2c1550bf73d2"))
        self.assertFalse(
            is_weaviate_entity_url("weaviate://localhost/nachos/28f3f61b-b524-45e0-9bbe-2c1550bf73d2"))
        self.assertFalse(
            is_weaviate_entity_url("weaviate://localhost/things/f61b-b524-45e0-9bbe-2c1550bf73d2"))

    def test_is_object_url(self):
        self.assertTrue(
            is_object_url("http://localhost:8080/v1/things/1c9cd584-88fe-5010-83d0-017cb3fcb446")
        )
        self.assertTrue(
            is_object_url("http://ramalamadingdong/v1/things/1c9cd584-88fe-5010-83d0-017cb3fcb446")
        )
        self.assertFalse(
            # not valid uuid
            is_object_url("http://ramalamadingdong/v1/things/1c9cd584-88fe-5010-83d0")
        )
        self.assertTrue(
            is_object_url("http://localhost:8080/v1/actions/1c9cd584-88fe-5010-83d0-017cb3fcb446")
        )
        self.assertFalse(
            is_object_url("http://localhost:8080/v1/1c9cd584-88fe-5010-83d0-017cb3fcb446")
        )
        self.assertFalse(
            is_object_url("http://localhost:8080/v1/passions/1c9cd584-88fe-5010-83d0-017cb3fcb446")
        )

    def test_parsed_uuid(self):
        p = ParsedUUID("weaviate://localhost/things/28f3f61b-b524-45e0-9bbe-2c1550bf73d2")
        self.assertEqual("28f3f61b-b524-45e0-9bbe-2c1550bf73d2", p.uuid)
        self.assertEqual(SEMANTIC_TYPE_THINGS, p.semantic_type)
        self.assertTrue(p.is_valid)
        self.assertTrue(p.is_weaviate_url)
        self.assertFalse(p.is_object_url)

        p = ParsedUUID("weaviate://localhost/actions/28f3f61b-b524-45e0-9bbe-2c1550bf73d2")
        self.assertEqual("28f3f61b-b524-45e0-9bbe-2c1550bf73d2", p.uuid)
        self.assertEqual(SEMANTIC_TYPE_ACTIONS, p.semantic_type)
        self.assertTrue(p.is_valid)
        self.assertTrue(p.is_weaviate_url)
        self.assertFalse(p.is_object_url)

        p = ParsedUUID("http://localhost:8080/v1/things/1c9cd584-88fe-5010-83d0-017cb3fcb446")
        self.assertEqual("1c9cd584-88fe-5010-83d0-017cb3fcb446", p.uuid)
        self.assertEqual(SEMANTIC_TYPE_THINGS, p.semantic_type)
        self.assertTrue(p.is_valid)
        self.assertFalse(p.is_weaviate_url)
        self.assertTrue(p.is_object_url)

        p = ParsedUUID("http://localhost:8080/v1/actions/1c9cd584-88fe-5010-83d0-017cb3fcb446")
        self.assertEqual("1c9cd584-88fe-5010-83d0-017cb3fcb446", p.uuid)
        self.assertEqual(SEMANTIC_TYPE_ACTIONS, p.semantic_type)
        self.assertTrue(p.is_valid)
        self.assertFalse(p.is_weaviate_url)
        self.assertTrue(p.is_object_url)

        p = ParsedUUID("http://localhost:8080/v1/actions/1c9cd584-88fe-5010-83d0-017cb3fcb")
        self.assertFalse(p.is_valid)

        p = ParsedUUID("1c9cd584-88fe-5010-83d0-017cb3fcb446")
        self.assertEqual("1c9cd584-88fe-5010-83d0-017cb3fcb446", p.uuid)
        self.assertEqual(None, p.semantic_type)
        self.assertTrue(p.is_valid)
        self.assertFalse(p.is_weaviate_url)
        self.assertFalse(p.is_object_url)

        try:
            ParsedUUID(2)
            self.fail("Expected type error")
        except TypeError:
            pass


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
    "objects": {
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
            },
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
    }
}
#     def test_generate_local_beacon(self):
#         try:
#             weaviate.generate_local_beacon(None)
#             self.fail("TypeError expected should be str")
#         except TypeError:
#             pass
#         try:
#             weaviate.generate_local_beacon("Leeroy Jenkins")
#             self.fail("Value error expected should be uuid")
#         except ValueError:
#             pass

#         beacon = weaviate.generate_local_beacon("fcf33178-1b5d-5174-b2e7-04a2129dd35a")
#         self.assertTrue("beacon" in beacon)
#         self.assertEqual(beacon["beacon"], "weaviate://localhost/things/fcf33178-1b5d-5174-b2e7-04a2129dd35a")

#         beacon = weaviate.generate_local_beacon("fcf33178-1b5d-5174-b2e7-04a2129dd35b", semantic_type=SEMANTIC_TYPE_ACTIONS)
#         self.assertTrue("beacon" in beacon)
#         self.assertEqual(beacon["beacon"], "weaviate://localhost/actions/fcf33178-1b5d-5174-b2e7-04a2129dd35b")