import unittest
from weaviate.schema.validate_schema import validate_schema, check_class, check_property
from weaviate.exceptions import SchemaValidationException


class TestSchemaValidation(unittest.TestCase):

    def test_schema_validation(self):
        """
        Test schema validation
        """

        schema_valid = {"classes": []}
        schema_invalid_0 = {"classes": "my_class"}
        schema_invalid_1 = {"things": {"classes": []}}
        schema_invalid_2 = {"classes": [], "things" : []}
        schema_none = {}

        self.assertIsNone(validate_schema(schema_valid))
        with self.assertRaises(SchemaValidationException):
            validate_schema(schema_none)
        with self.assertRaises(SchemaValidationException):
            validate_schema(schema_invalid_0)
        with self.assertRaises(SchemaValidationException):
            validate_schema(schema_invalid_1)
        with self.assertRaises(SchemaValidationException):
            validate_schema(schema_invalid_2)

    def test_check_class(self):
        """
        Test check_class.
        """

        # Valid maximal schema
        max_valid = {
            "class": "Boat",
            "description": "boat swiming on the water",
            "properties": [],
            "vectorIndexType": "hnsw",
            "vectorIndexConfig": {},
            "moduleConfig": {},
            "vectorizer": "text2vec-contextionary",
            }
        self.assertIsNone(check_class(max_valid))
        # minimal must contain class key as string
        self.assertIsNone(check_class({"class": "Car"}))

        # wrong type
        with self.assertRaises(SchemaValidationException):
            class_ = {"class" : []}
            check_class({
                "class" : [],
                "invalid_key": "value"
                })
        with self.assertRaises(SchemaValidationException):
            check_class({
                "class": "Tree",
                "description": []
                })
        with self.assertRaises(SchemaValidationException):
            check_class({
                "class": "Tree",
                "properties": "References please"
                })
        with self.assertRaises(SchemaValidationException):
            check_class({
                "class": "Tree",
                "vectorIndexType": True
                })
        with self.assertRaises(SchemaValidationException):
            check_class({
                "class": "Tree",
                "vectorIndexConfig": []
                })
        with self.assertRaises(SchemaValidationException):
            check_class({
                "class": "Tree",
                "moduleConfig": []
                })
        with self.assertRaises(SchemaValidationException):
            check_class({
                "class": "Tree",
                "vectorizer": 100.1
                })

    def test_check_property(self):
        """
        Test check_property.
        """

        valid_minimal = {"dataType": ["string"],
                         "name": "string"}
        self.assertIsNone(check_property(valid_minimal))
        valid_max = {
            "dataType": ["string"],
            "name": "Rocket",
            "moduleConfig": {},
            "description": "some description",
            "indexInverted": True
        }
        self.assertIsNone(check_property(valid_max))

        with self.assertRaises(SchemaValidationException):
            properties = {
                "dataType": ["string"]
                }
            check_property(properties)
        with self.assertRaises(SchemaValidationException):
            properties = {
                "name": "string"
                }
            check_property(properties)
        with self.assertRaises(SchemaValidationException):
            properties = {
                "dataType": ["string"],
                "name": "string",
                "invalid_property": "value"
                }
            check_property(properties)
        with self.assertRaises(SchemaValidationException):
            properties = {
                "dataType": ["string"],
                "name": "Rocket",
                "moduleConfig": [],
            }
            check_property(properties)
        with self.assertRaises(SchemaValidationException):
            properties = {
                "dataType": ["string"],
                "name": "Rocket",
                "description": ["some description"],
            }
            check_property(properties)
        with self.assertRaises(SchemaValidationException):
            properties = {
                "dataType": ["string"],
                "name": "Rocket",
                "indexInverted": "True"
            }
            check_property(properties)
        with self.assertRaises(SchemaValidationException):
            properties = {
                "dataType": ["string", 10],
                "name": "Rocket",
                "indexInverted": "True"
            }
            check_property(properties)
