import unittest
from unittest.mock import Mock

from requests import exceptions

from weaviate.exceptions import (
    UnexpectedStatusCodeException,
    ObjectAlreadyExistsException,
    AuthenticationFailedException,
    SchemaValidationException,
)


class TestExceptions(unittest.TestCase):
    def test_unexpected_status_code(self):
        """
        Test the `UnexpectedStatusCodeException` exception.
        """

        # with .json() exception raised
        response = Mock()
        response.json = Mock(side_effect=exceptions.JSONDecodeError("test", "", 0))
        response.status_code = 1234
        exception = UnexpectedStatusCodeException(message="Test message", response=response)
        self.assertEqual(
            str(exception), "Test message! Unexpected status code: 1234, with response body: None."
        )
        self.assertEqual(exception.status_code, response.status_code)

        # with .json() value
        response = Mock()
        response.json = Mock()
        response.json.return_value = {"test": "OK!"}
        response.status_code = 4321
        exception = UnexpectedStatusCodeException(message="Second test message", response=response)
        self.assertEqual(
            str(exception),
            "Second test message! Unexpected status code: 4321, with response body: {'test': 'OK!'}.",
        )
        self.assertEqual(exception.status_code, response.status_code)

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
