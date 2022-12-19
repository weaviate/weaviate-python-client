import unittest
from weaviate.schema.validate_schema import validate_schema, check_class, check_property
from weaviate.exceptions import SchemaValidationException
from test.util import check_error_message


valid_schema_with_all_properties = {
    "classes": [
        {
            "class": "Category",
            "description": "Category an article is a type off",
            "moduleConfig": {"text2vec-contextionary": {"vectorizeClassName": False}},
            "properties": [
                {
                    "dataType": ["string"],
                    "description": "category name",
                    "indexInverted": True,
                    "moduleConfig": {"text2vec-contextionary": {"vectorizePropertyName": False}},
                    "name": "name",
                }
            ],
            "vectorIndexType": "hnsw",
            "vectorizer": "none",
            "replicationConfig": {
                "factor": 1,
            },
        },
        {
            "class": "Publication",
            "description": "A publication with an online source",
            "moduleConfig": {"text2vec-contextionary": {"vectorizeClassName": False}},
            "properties": [
                {"dataType": ["string"], "description": "Name of the publication", "name": "name"},
                {
                    "dataType": ["geoCoordinates"],
                    "description": "Geo location of the HQ",
                    "name": "headquartersGeoLocation",
                },
                {
                    "dataType": ["Article"],
                    "description": "The articles this publication has",
                    "name": "hasArticles",
                },
                {
                    "dataType": ["Article"],
                    "description": "Articles this author wrote",
                    "name": "wroteArticles",
                },
            ],
            "vectorIndexType": "hnsw",
            "vectorizer": "none",
            "replicationConfig": {
                "factor": 1,
            },
        },
        {
            "class": "Author",
            "description": "Normalised types",
            "moduleConfig": {"text2vec-contextionary": {"vectorizeClassName": True}},
            "properties": [
                {"dataType": ["string"], "description": "Name of the author", "name": "name"},
                {
                    "dataType": ["Publication"],
                    "description": "The publication this author writes for",
                    "name": "writesFor",
                },
            ],
            "vectorIndexType": "hnsw",
            "vectorizer": "none",
            "replicationConfig": {
                "factor": 1,
            },
        },
        {
            "class": "Article",
            "description": "Normalised types",
            "moduleConfig": {"text2vec-contextionary": {"vectorizeClassName": False}},
            "properties": [
                {
                    "dataType": ["string"],
                    "description": "title of the article",
                    "indexInverted": True,
                    "moduleConfig": {"text2vec-contextionary": {"vectorizePropertyName": False}},
                    "name": "title",
                },
                {
                    "dataType": ["string"],
                    "description": "url of the article",
                    "indexInverted": False,
                    "moduleConfig": {"text2vec-contextionary": {"vectorizePropertyName": False}},
                    "name": "url",
                },
                {
                    "dataType": ["text"],
                    "description": "summary of the article",
                    "indexInverted": True,
                    "moduleConfig": {"text2vec-contextionary": {"vectorizePropertyName": False}},
                    "name": "summary",
                },
                {
                    "dataType": ["date"],
                    "description": "date of publication of the article",
                    "name": "publicationDate",
                },
                {"dataType": ["int"], "description": "Words in this article", "name": "wordCount"},
                {
                    "dataType": ["Author", "Publication"],
                    "description": "authors this article has",
                    "name": "hasAuthors",
                },
                {
                    "dataType": ["Publication"],
                    "description": "publication this article is in",
                    "name": "inPublication",
                },
                {
                    "dataType": ["Category"],
                    "description": "category this article is of",
                    "name": "ofCategory",
                },
                {
                    "dataType": ["boolean"],
                    "description": "whether the article is currently accessible through the url",
                    "name": "isAccessible",
                },
            ],
            "vectorIndexType": "hnsw",
            "vectorizer": "none",
            "replicationConfig": {
                "factor": 1,
            },
        },
    ]
}


class TestSchemaValidation(unittest.TestCase):
    def test_validate_schema(self):
        """
        Test `validate_schema` function.
        """

        # invalid calls
        classess_error_message = (
            'Each schema has to have "classes" '
            "in the first level of the JSON format file/parameter/object"
        )
        class_key_error_message = '"class" key is missing in class definition.'

        invalid_schema = {}
        with self.assertRaises(SchemaValidationException) as error:
            validate_schema(invalid_schema)
        check_error_message(self, error, classess_error_message)

        invalid_schema = {"classes": "my_class"}
        with self.assertRaises(SchemaValidationException) as error:
            validate_schema(invalid_schema)
        check_error_message(self, error, f'"classes" is type {str} but should be {list}.')

        invalid_schema = {"things": {"classes": []}}
        with self.assertRaises(SchemaValidationException) as error:
            validate_schema(invalid_schema)
        check_error_message(self, error, classess_error_message)

        invalid_schema = {"classes": ["my_class"]}
        with self.assertRaises(SchemaValidationException) as error:
            validate_schema(invalid_schema)
        check_error_message(self, error, f'"class" is type {str} but should be {dict}.')

        # test the call of the `check_class` function inside `validate_schema`
        invalid_schema = {"classes": [{"my_class": []}]}
        with self.assertRaises(SchemaValidationException) as error:
            validate_schema(invalid_schema)
        check_error_message(self, error, class_key_error_message)

        # valid calls
        valid_schema = {"classes": []}
        self.assertIsNone(validate_schema(valid_schema))
        valid_schema = {"classes": [], "author": "Unit Test"}
        self.assertIsNone(validate_schema(valid_schema))
        self.assertIsNone(validate_schema(valid_schema_with_all_properties))

    def test_check_class(self):
        """
        Test `check_class` function.
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
            "replicationConfig": {
                "factor": 1,
            },
        }
        check_class(max_valid)
        # minimal must contain class key as string
        check_class({"class": "Car"})

        # invalid calls
        class_key_error_message = '"class" key is missing in class definition.'
        unknown_key_error_message = lambda key: f'"{key}" is not a known class definition key.'
        key_type_error_messsage = lambda key, value, exp_type: (
            f'"{key}" is type {type(value)} ' f"but should be {exp_type}."
        )

        with self.assertRaises(SchemaValidationException) as error:
            check_class({"invalid_key": "value"})
        check_error_message(self, error, class_key_error_message)

        with self.assertRaises(SchemaValidationException) as error:
            check_class(
                {
                    "class": [],
                }
            )
        check_error_message(self, error, key_type_error_messsage("class", [], str))

        with self.assertRaises(SchemaValidationException) as error:
            check_class({"class": "Tree", "invalid_key": []})
        check_error_message(self, error, unknown_key_error_message("invalid_key"))

        with self.assertRaises(SchemaValidationException) as error:
            check_class({"class": "Tree", "description": []})
        check_error_message(self, error, key_type_error_messsage("description", [], str))

        with self.assertRaises(SchemaValidationException) as error:
            check_class({"class": "Tree", "properties": "References please"})
        check_error_message(self, error, key_type_error_messsage("properties", "", list))

        with self.assertRaises(SchemaValidationException) as error:
            check_class({"class": "Tree", "vectorIndexType": True})
        check_error_message(self, error, key_type_error_messsage("vectorIndexType", True, str))

        with self.assertRaises(SchemaValidationException) as error:
            check_class({"class": "Tree", "vectorIndexConfig": []})
        check_error_message(self, error, key_type_error_messsage("vectorIndexConfig", [], dict))

        with self.assertRaises(SchemaValidationException) as error:
            check_class({"class": "Tree", "replicationConfig": []})
        check_error_message(self, error, key_type_error_messsage("replicationConfig", [], dict))

        with self.assertRaises(SchemaValidationException) as error:
            check_class({"class": "Tree", "moduleConfig": []})
        check_error_message(self, error, key_type_error_messsage("moduleConfig", [], dict))

        with self.assertRaises(SchemaValidationException) as error:
            check_class({"class": "Tree", "vectorizer": 100.1})
        check_error_message(self, error, key_type_error_messsage("vectorizer", 100.1, str))

        # check if `check_property` is called inside `check_class`
        with self.assertRaises(SchemaValidationException) as error:
            check_class(
                {
                    "class": "Tree",
                    "properties": [
                        {
                            "dataType": ["string"],
                            "description": "Test Property",
                        }
                    ],
                }
            )
        check_error_message(self, error, 'Property does not contain "name"')

    def test_check_property(self):
        """
        Test `check_property` function.
        """

        # valid calls
        valid_minimal = {"dataType": ["string"], "name": "string"}

        check_property(valid_minimal)
        valid_max = {
            "dataType": ["string"],
            "name": "Rocket",
            "moduleConfig": {},
            "description": "some description",
            "indexInverted": True,
        }
        check_property(valid_max)

        # invalid calls
        data_type_error_message = 'Property does not contain "dataType"'
        name_error_message = 'Property does not contain "name"'
        key_error_message = lambda key: f'Property "{key}" is not known.'
        key_type_error_messsage = lambda key, value, exp_type: (
            f'"{key}" is type {type(value)} ' f"but should be {exp_type}."
        )

        properties = {"dataType": ["string"]}
        with self.assertRaises(SchemaValidationException) as error:
            check_property(properties)
        check_error_message(self, error, name_error_message)

        properties = {"name": "string"}
        with self.assertRaises(SchemaValidationException) as error:
            check_property(properties)
        check_error_message(self, error, data_type_error_message)

        properties = {"dataType": ["string"], "name": "string", "invalid_property": "value"}
        with self.assertRaises(SchemaValidationException) as error:
            check_property(properties)
        check_error_message(self, error, key_error_message("invalid_property"))

        properties = {
            "dataType": ["string"],
            "name": "Rocket",
            "moduleConfig": [],
        }
        with self.assertRaises(SchemaValidationException) as error:
            check_property(properties)
        check_error_message(
            self, error, key_type_error_messsage("moduleConfig", properties["moduleConfig"], dict)
        )

        properties = {
            "dataType": ["string"],
            "name": "Rocket",
            "description": ["some description"],
        }
        with self.assertRaises(SchemaValidationException) as error:
            check_property(properties)
        check_error_message(
            self, error, key_type_error_messsage("description", properties["description"], str)
        )

        properties = {"dataType": ["string"], "name": "Rocket", "indexInverted": "True"}
        with self.assertRaises(SchemaValidationException) as error:
            check_property(properties)
        check_error_message(
            self, error, key_type_error_messsage("indexInverted", properties["indexInverted"], bool)
        )

        properties = {"dataType": ["string", 10], "name": "Rocket", "indexInverted": True}
        with self.assertRaises(SchemaValidationException) as error:
            check_property(properties)
        check_error_message(
            self, error, key_type_error_messsage("dataType object", properties["dataType"][1], str)
        )
