import unittest
import weaviate
from weaviate.exceptions import RequestsConnectionError, UnexpectedStatusCodeException
from weaviate.connect import REST_METHOD_POST, REST_METHOD_DELETE
from test.util import replace_connection, mock_run_rest


class TestCRUDProperty(unittest.TestCase):

    def test_create(self):
        """
        Test `create` method.
        """

        client = weaviate.Client("http://localhorst:8080")

        # invalid calls
        error_message = "Class name must be of type str but is "
        check_property_error_message = 'Property does not contain "dataType"'
        requests_error_message =  (' Connection error, property may not have '
                                        'been created properly.')

        with self.assertRaises(TypeError) as error:
            client.schema.property.create(35, {})
        self.assertEqual(str(error.exception), error_message + str(int))

        # test if `check_property` is called in `create`
        with self.assertRaises(weaviate.SchemaValidationException) as error:
            client.schema.property.create("Class", {})
        self.assertEqual(str(error.exception), check_property_error_message)

        replace_connection(client, mock_run_rest(side_effect=RequestsConnectionError('Test!')))
        with self.assertRaises(RequestsConnectionError) as error:
            client.schema.property.create("Class", {"name": 'test', 'dataType': ["test_type"]})
        self.assertEqual(str(error.exception), 'Test!' + requests_error_message)

        replace_connection(client, mock_run_rest(status_code=404))
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            client.schema.property.create("Class", {"name": 'test', 'dataType': ["test_type"]})
        self.assertTrue(str(error.exception).startswith("Add property to class"))

        # valid calls
        connection_mock = mock_run_rest() # Mock calling weaviate
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

    # def test_delete(self):
    #     """
    #     Test `_delete` method. (currently not available)
    #     """

    #     # invalid calls
    #     client = weaviate.Client("http://localhorst:8080")

    #     with self.assertRaises(TypeError):
    #         client.schema.property._delete("Class", 4)
    #     with self.assertRaises(TypeError):
    #         client.schema.property._delete(35, "prop")

    #     # valid calls
    #     connection_mock = mock_run_rest() # Mock calling weaviate
    #     replace_connection(client, connection_mock)

    #     client.schema.property._delete("ThingClass", "propUno")

    #     connection_mock.run_rest.assert_called()

    #     call_args_list = connection_mock.run_rest.call_args_list
    #     call_args = call_args_list[0][0]

    #     self.assertEqual("/schema/ThingClass/properties/propUno", call_args[0])
    #     self.assertEqual(REST_METHOD_DELETE, call_args[1])
