import unittest
import weaviate
from weaviate.connect import REST_METHOD_POST, REST_METHOD_DELETE
from test.testing_util import replace_connection, add_run_rest_to_mock, Mock


class TestCRUDProperty(unittest.TestCase):

    def test_create_bad_input(self):
        """
        Test create property exceptions.
        """

        client = weaviate.Client("http://localhorst:8080")
        test_prop = {
            "dataType": ["string"],
            "description": "my Property",
            "moduleConfig" : {
                "text2vec-contextionary": {
                    "vectorizePropertyName": True
                }
            },
            # "name": "superProp", missing name
            "indexInverted": True
        }

        with self.assertRaises(weaviate.SchemaValidationException):
            client.schema.property.create("Class", test_prop)
        test_prop["name"] = "someName"
        with self.assertRaises(TypeError):
            client.schema.property.create(35, test_prop)
        with self.assertRaises(TypeError):
            client.schema.property.create("Class", ["wrong", "type"])

    def test_create(self):
        """
        Test create.
        """

        client = weaviate.Client("http://localhorst:8080")

        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock)
        replace_connection(client, connection_mock)

        test_prop = {
            "dataType": ["string"],
            "description": "my Property",
            "moduleConfig" : {
                "text2vec-contextionary": {
                    "vectorizePropertyName": True
                }
            },
            "name": "superProp",
            "indexInverted": True
        }

        client.schema.property.create("TestThing", test_prop)

        connection_mock.run_rest.assert_called()

        call_args_list = connection_mock.run_rest.call_args_list
        call_args = call_args_list[0][0]

        self.assertEqual("/schema/TestThing/properties", call_args[0])
        self.assertEqual(REST_METHOD_POST, call_args[1])
        self.assertEqual(test_prop, call_args[2])

    def test_delete_bad_input(self):
        """
        Test create with bad input.
        """

        client = weaviate.Client("http://localhorst:8080")

        with self.assertRaises(TypeError):
            client.schema.property._delete("Class", 4)
        with self.assertRaises(TypeError):
            client.schema.property._delete(35, "prop")

    def test_delete(self):
        """
        Test delete property. (currently not available)
        """

        client = weaviate.Client("http://localhorst:8080")

        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock)
        replace_connection(client, connection_mock)

        client.schema.property._delete("ThingClass", "propUno")

        connection_mock.run_rest.assert_called()

        call_args_list = connection_mock.run_rest.call_args_list
        call_args = call_args_list[0][0]

        self.assertEqual("/schema/ThingClass/properties/propUno", call_args[0])
        self.assertEqual(REST_METHOD_DELETE, call_args[1])
