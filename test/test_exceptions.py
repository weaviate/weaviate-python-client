import unittest
from unittest.mock import Mock
from weaviate.exceptions import *


class TestExceptions(unittest.TestCase):

    def test_unexpected_status_code(self):
        """
        Test the `UnexpectedStatusCodeException` exception.
        """

        # with .json() exception raised
        response = Mock()
        response.json = Mock()
        response.json.side_effect = Exception("Test")
        response.status_code = 1234
        exception = UnexpectedStatusCodeException(message="Test message", response=response)

        self.assertEqual(exception.status_code, 1234)
        self.assertIsNone(exception.json)
        self.assertEqual(str(exception), "Test message! Unexpected status code: 1234, with response body: None")

        # with .json() value
        response = Mock()
        response.json = Mock()
        response.json.return_value = {"test" : "OK!"}
        response.status_code = 4321
        exception = UnexpectedStatusCodeException(message="Second test message", response=response)

        self.assertEqual(exception.status_code, 4321)
        self.assertEqual(exception.json, {"test" : "OK!"})
        self.assertEqual(str(exception), "Second test message! Unexpected status code: 4321, with response body: {'test': 'OK!'}")

    def test_object_already_exists(self):
        """
        Test the `ObjectAlreadyExistsException` exception.
        """

        exception = ObjectAlreadyExistsException("Test")
        self.assertEqual(str(exception), "Test")

    def test_authentication_failed(self):
        """
        Test the `AuthenticationFailedException` exception.
        """

        exception = AuthenticationFailedException("Test")
        self.assertEqual(str(exception), "Test")

    def test_schema_validation(self):
        """
        Test the `SchemaValidationException` exception.
        """

        exception = SchemaValidationException("Test")
        self.assertEqual(str(exception), "Test")