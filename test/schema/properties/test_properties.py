import unittest
from unittest.mock import Mock

from requests.exceptions import ConnectionError as RequestsConnectionError

from test.util import mock_connection_func, check_error_message, check_startswith_error_message
from weaviate.exceptions import (
    UnexpectedStatusCodeException,
)
from weaviate.schema.properties import Property


class TestCRUDProperty(unittest.TestCase):
    def test_create(self):
        """
        Test `create` method.
        """

        prop = Property(Mock())

        # invalid calls
        error_message = "Class name must be of type str but is "
        requests_error_message = "Property was created properly."

        with self.assertRaises(TypeError) as error:
            prop.create(35, {})
        check_error_message(self, error, error_message + str(int))

        prop = Property(mock_connection_func("post", side_effect=RequestsConnectionError("Test!")))
        with self.assertRaises(RequestsConnectionError) as error:
            prop.create("Class", {"name": "test", "dataType": ["test_type"]})
        check_error_message(self, error, requests_error_message)

        prop = Property(mock_connection_func("post", status_code=404))
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            prop.create("Class", {"name": "test", "dataType": ["test_type"]})
        check_startswith_error_message(self, error, "Add property to class")

        # valid calls
        connection_mock = mock_connection_func("post")  # Mock calling weaviate
        prop = Property(connection_mock)

        test_prop = {
            "dataType": ["string"],
            "description": "my Property",
            "moduleConfig": {"text2vec-contextionary": {"vectorizePropertyName": True}},
            "name": "superProp",
            "indexInverted": True,
        }

        prop.create("TestThing", test_prop)

        connection_mock.post.assert_called_with(
            path="/schema/TestThing/properties",
            weaviate_object=test_prop,
        )

        prop.create("testThing", test_prop)

        connection_mock.post.assert_called_with(
            path="/schema/TestThing/properties",
            weaviate_object=test_prop,
        )
