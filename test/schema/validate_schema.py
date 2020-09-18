import unittest
from weaviate.schema.validate_schema import validate_schema, \
    _check_schema_class_types, check_class, check_property

from weaviate.exceptions import SchemaValidationException


class TestSchemaValidation(unittest.TestCase):

    def test_actions_and_things(self):
        schema_things = {"things": {"classes": []}}
        schema_actions = {"actions": {"classes": []}}
        schema_both = {"actions": {"classes": []},
                       "things": {"classes": []}}
        schema_none = {}
        schema_wrong = {"thinks": {"classes": []}}
        schema_too_much = {"actions": {"classes": []},
                           "things": {"classes": []},
                           "memories": {"classes": []}}


        self.assertIsNone(validate_schema(schema_things))
        self.assertIsNone(validate_schema(schema_actions))
        self.assertIsNone(validate_schema(schema_both))
        try:
            validate_schema(schema_none)
            self.fail("expected exception")
        except SchemaValidationException:
            pass
        try:
            validate_schema(schema_too_much)
            self.fail("expected exception")
        except SchemaValidationException:
            pass
        try:
            validate_schema(schema_wrong)
            self.fail("expected exception")
        except SchemaValidationException:
            pass

    def test_check_schema_class_types(self):
        with_classes = {"classes": []}
        no_classes = {"random": "field"}
        with_classes_and_others = {"@context": "",
                                   "version": "0.2.0",
                                   "type": "thing",
                                   "name": "people",
                                   "maintainer": "yourfriends@weaviate.com",
                                   "classes": []}
        self.assertIsNone(_check_schema_class_types("things", with_classes))
        self.assertIsNone(_check_schema_class_types("things", with_classes_and_others))
        try:
            _check_schema_class_types("things", no_classes)
            self.fail("expected exception")
        except SchemaValidationException:
            pass
        # test classes not a list
        try:
            _check_schema_class_types("things", {"classes": "a"})
            self.fail("expected exception")
        except SchemaValidationException:
            pass

    def test_check_class(self):
        # minimal must contain class key as string
        check_class({"class": "Car"})
        try:
            # wrong type
            check_class({"class": []})
            self.fail()
        except SchemaValidationException:
            pass

        # Valid maximal schema
        max_valid = {"class": "Boat",
                     "description": "boat swiming on the water",
                     "vectorizeClassName": True,
                     "keywords": [],
                     "properties": []}

        check_class(max_valid)

        try:
            # unknown key
            max_valid["random"] = "field"
            check_class(max_valid)
            self.fail()
        except SchemaValidationException:
            pass

        # Check data types optional fields
        try:
            check_class({"class": "Tree",
                          "description": []})
            self.fail()
        except SchemaValidationException:
            pass
        try:
            check_class({"class": "Tree",
                          "vectorizeClassName": "yes"})
            self.fail()
        except SchemaValidationException:
            pass
        try:
            check_class({"class": "Tree",
                          "keywords": "all of them"})
            self.fail()
        except SchemaValidationException:
            pass
        try:
            check_class({"class": "Tree",
                          "properties": "References please"})
            self.fail()
        except SchemaValidationException:
            pass

    def test_check_property(self):
        valid_minimal = {"dataType": ["string"],
                         "name": "string"}
        check_property(valid_minimal)
        valid_max = {"dataType": ["string"],
                     "name": "Rocket",
                     "vectorizePropertyName": True,
                     "keywords": [],
                     "cardinality": "many",
                     "description": "some description",
                     "index": True}
        check_property(valid_max)
        try:
            # unknown field
            valid_minimal["random"] = "field"
            check_property(valid_minimal)
            self.fail()
        except SchemaValidationException:
            pass
        # Wrong data types:
        try:
            check_property({"dataType": "not list",
                             "name": "Rocket",
                             "vectorizePropertyName": True,
                             "keywords": [],
                             "cardinality": "many",
                             "description": "some description",
                             "index": True})
            self.fail()
        except SchemaValidationException:
            pass
        try:
            check_property({"dataType": ["string"],
                             "name": 12,
                             "vectorizePropertyName": True,
                             "keywords": [],
                             "cardinality": "many",
                             "description": "some description",
                             "index": True})
            self.fail()
        except SchemaValidationException:
            pass
        try:
            check_property({"dataType": ["string"],
                             "name": "Rocket",
                             "vectorizePropertyName": "Yes",
                             "keywords": [],
                             "cardinality": "many",
                             "description": "some description",
                             "index": True})
            self.fail()
        except SchemaValidationException:
            pass
        try:
            check_property({"dataType": ["string"],
                             "name": "Rocket",
                             "vectorizePropertyName": True,
                             "keywords": "not list",
                             "cardinality": "many",
                             "description": "some description",
                             "index": True})
            self.fail()
        except SchemaValidationException:
            pass
        try:
            check_property({"dataType": ["string"],
                             "name": "Rocket",
                             "vectorizePropertyName": True,
                             "keywords": [],
                             "cardinality": 1,
                             "description": "some description",
                             "index": True})
            self.fail()
        except SchemaValidationException:
            pass
        try:
            check_property({"dataType": ["string"],
                             "name": "Rocket",
                             "vectorizePropertyName": True,
                             "keywords": [],
                             "cardinality": "many",
                             "description": 3,
                             "index": True})
            self.fail()
        except SchemaValidationException:
            pass
        try:
            check_property({"dataType": ["string"],
                             "name": "Rocket",
                             "vectorizePropertyName": True,
                             "keywords": [],
                             "cardinality": "many",
                             "description": "some description",
                             "index": "Yes"})
            self.fail()
        except SchemaValidationException:
            pass
        # Wrong cardinality
        try:
            check_property({"dataType": ["string"],
                             "name": "Rocket",
                             "vectorizePropertyName": True,
                             "keywords": [],
                             "cardinality": "aLot",
                             "description": "some description",
                             "index": True})
            self.fail()
        except SchemaValidationException:
            pass
