import unittest
from unittest.mock import Mock
import weaviate
from weaviate.connect import REST_METHOD_POST, REST_METHOD_GET
from weaviate.exceptions import RequestsConnectionError, UnexpectedStatusCodeException
from test.util import mock_run_rest, replace_connection


class TestText2VecContextionary(unittest.TestCase):

    def test_extend(self):
        """
        Test `extend` method.
        """

        client = weaviate.Client("http://weaviate:8080")

        some_concept = {
            "concept" : "lsd",
            "definition" : "In probability and statistics, the logarithmic series distribution is a discrete probability distribution derived from the Maclaurin series expansion"
        }

        # error messages
        concept_type_error_message = "Concept must be string"
        definition_type_error_message = "Definition must be string"
        weight_type_error_message = "Weight must be float"
        weight_value_error_message = "Weight out of limits 0.0 <= weight <= 1.0"
        requests_error_message = 'Test! Connection error, text2vec-contextionary could not be extended.'
        unexpected_error_message = "Extend text2vec-contextionary"

        ## test exceptions
        with self.assertRaises(TypeError) as error:
            client.contextionary.extend(concept=None, definition=some_concept["definition"], weight=1.0)
        self.assertEqual(str(error.exception), concept_type_error_message)

        with self.assertRaises(TypeError) as error:
            client.contextionary.extend(concept=some_concept["concept"], definition=None, weight=1.0)
        self.assertEqual(str(error.exception), definition_type_error_message)

        with self.assertRaises(TypeError) as error:
            client.contextionary.extend(**some_concept, weight=None)
        self.assertEqual(str(error.exception), weight_type_error_message)

        with self.assertRaises(ValueError) as error:
            client.contextionary.extend(**some_concept, weight=1.1)
        self.assertEqual(str(error.exception), weight_value_error_message)

        with self.assertRaises(ValueError) as error:
            client.contextionary.extend(**some_concept, weight=-1.0)
        self.assertEqual(str(error.exception), weight_value_error_message)

        ## test UnexpectedStatusCodeException
        connection_mock = mock_run_rest(status_code=404)
        replace_connection(client, connection_mock)
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            client.contextionary.extend(**some_concept)
        self.assertTrue(str(error.exception).startswith(unexpected_error_message))

        ## test requests error
        connection_mock = mock_run_rest(side_effect=RequestsConnectionError("Test!"))
        replace_connection(client, connection_mock)
        with self.assertRaises(weaviate.RequestsConnectionError) as error:
            client.contextionary.extend(**some_concept)
        self.assertEqual(str(error.exception), requests_error_message)
        
        ## test valid call without specifying 'weight'
        some_concept["weight"] = 1.0
        connection_mock = mock_run_rest(status_code=200)
        replace_connection(client, connection_mock)
        client.contextionary.extend(**some_concept)
        connection_mock.run_rest.assert_called_with(
            "/modules/text2vec-contextionary/extensions",
            REST_METHOD_POST,
            some_concept
        )

        ## test valid call with specifying 'weight as error'
        connection_mock = mock_run_rest(status_code=200)
        replace_connection(client, connection_mock)
        # add weigth to 'some_concept'
        some_concept["weight"] = .1234
        client.contextionary.extend(**some_concept)
        connection_mock.run_rest.assert_called_with(
            "/modules/text2vec-contextionary/extensions",
            REST_METHOD_POST,
            some_concept
        )

    def test_get_concept_vector(self):
        """
        Test `get_concept_vector` method.
        """

        client = weaviate.Client("http://citadelofricks.city:6969")

        # test valid call
        connection_mock = mock_run_rest(return_json={"A": "B"})
        replace_connection(client, connection_mock)
        self.assertEqual("B", client.contextionary.get_concept_vector("sauce")["A"])
        connection_mock.run_rest.assert_called_with(
            "/modules/text2vec-contextionary/concepts/sauce",
            REST_METHOD_GET,
        )

        # test exceptions

        # error messages
        requests_error_message = 'Test! Connection error, text2vec-contextionary vector was not retrieved.'
        unexpected_exception_error_message = "text2vec-contextionary vector"
        unexpected_error_message = 'Test Unexpected exception please report this excetpion in an issue.'

        ## test UnexpectedStatusCodeException
        replace_connection(client, mock_run_rest(status_code=404))
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            client.contextionary.get_concept_vector("Palantir")
        self.assertTrue(str(error.exception).startswith(unexpected_exception_error_message))

        ## test requests error
        replace_connection(client, mock_run_rest(side_effect=RequestsConnectionError("Test!")))
        with self.assertRaises(RequestsConnectionError) as error:
            client.contextionary.get_concept_vector("Palantir")
        self.assertEqual(str(error.exception), requests_error_message)

        ## test unexpected error
        replace_connection(client, mock_run_rest(side_effect=Exception("Test")))
        with self.assertRaises(Exception) as error:
            client.contextionary.get_concept_vector("Palantir")
        self.assertEqual(str(error.exception), unexpected_error_message)
