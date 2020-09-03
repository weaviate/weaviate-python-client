import unittest
import weaviate
from weaviate import SEMANTIC_TYPE_ACTIONS
from weaviate.connect import REST_METHOD_POST, REST_METHOD_DELETE
from unittest.mock import Mock
from test.testing_util import replace_connection, add_run_rest_to_mock


class TestCRUDProperty(unittest.TestCase):

    def test_create_bad_input(self):
        w = weaviate.Client("http://localhorst:8080")
        test_prop = {
            "dataType": ["string"],
            "cardinality": "atMostOne",
            "description": "my Property",
            "vectorizePropertyName": True,
            # "name": "superProp", missing name
            "index": True
        }
        try:
            w.schema.property.create("Class", test_prop)
            self.fail("No error")
        except weaviate.SchemaValidationException:
            pass
        test_prop["name"] = "someName"
        try:
            w.schema.property.create(35, test_prop)
            self.fail("No error")
        except TypeError:
            pass
        try:
            w.schema.property.create("Class", ["wrong", "type"])
            self.fail("No error")
        except TypeError:
            pass

    def test_create(self):
        w = weaviate.Client("http://localhorst:8080")

        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock)
        replace_connection(w, connection_mock)

        test_prop = {
            "dataType": ["string"],
            "cardinality": "atMostOne",
            "description": "my Property",
            "vectorizePropertyName": True,
            "name": "superProp",
            "index": True
        }

        w.schema.property.create("TestThing", test_prop)
        w.schema.property.create("TestAction", test_prop, SEMANTIC_TYPE_ACTIONS)

        connection_mock.run_rest.assert_called()

        call_args_list = connection_mock.run_rest.call_args_list
        call_args, call_kwargs = call_args_list[0]

        self.assertEqual("/schema/things/TestThing/properties", call_args[0])
        self.assertEqual(REST_METHOD_POST, call_args[1])
        self.assertEqual(test_prop, call_args[2])

        call_args, call_kwargs = call_args_list[1]

        self.assertEqual("/schema/actions/TestAction/properties", call_args[0])
        self.assertEqual(REST_METHOD_POST, call_args[1])
        self.assertEqual(test_prop, call_args[2])

    def test_delete_bad_input(self):
        w = weaviate.Client("http://localhorst:8080")
        try:
            w.schema.property._delete("Class", 4)
            self.fail("No error")
        except TypeError:
            pass
        try:
            w.schema.property._delete(35, "prop")
            self.fail("No error")
        except TypeError:
            pass

    def test_delete(self):
        w = weaviate.Client("http://localhorst:8080")

        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock)
        replace_connection(w, connection_mock)

        w.schema.property._delete("ThingClass", "propUno")
        w.schema.property._delete("ActionClass", "propDos", SEMANTIC_TYPE_ACTIONS)

        connection_mock.run_rest.assert_called()

        call_args_list = connection_mock.run_rest.call_args_list
        call_args, call_kwargs = call_args_list[0]

        self.assertEqual("/schema/things/ThingClass/properties/propUno", call_args[0])
        self.assertEqual(REST_METHOD_DELETE, call_args[1])

        call_args, call_kwargs = call_args_list[1]

        self.assertEqual("/schema/actions/ActionClass/properties/propDos", call_args[0])
        self.assertEqual(REST_METHOD_DELETE, call_args[1])

