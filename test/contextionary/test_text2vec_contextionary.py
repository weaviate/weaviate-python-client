import unittest
from unittest.mock import Mock

from requests.exceptions import ConnectionError as RequestsConnectionError

from test.util import mock_connection_func, check_error_message, check_startswith_error_message
from weaviate.contextionary import Contextionary
from weaviate.exceptions import UnexpectedStatusCodeException


class TestText2VecContextionary(unittest.TestCase):
    def test_extend(self):
        """
        Test `extend` method.
        """

        contextionary = Contextionary(Mock())

        some_concept = {
            "concept": "lsd",
            "definition": "In probability and statistics, the logarithmic series distribution is a discrete probability distribution derived from the Maclaurin series expansion",
        }

        # error messages
        concept_type_error_message = "Concept must be string"
        definition_type_error_message = "Definition must be string"
        weight_type_error_message = "Weight must be float"
        weight_value_error_message = "Weight out of limits 0.0 <= weight <= 1.0"
        requests_error_message = "text2vec-contextionary could not be extended."
        unexpected_error_message = "Extend text2vec-contextionary"

        ## test exceptions
        with self.assertRaises(TypeError) as error:
            contextionary.extend(concept=None, definition=some_concept["definition"], weight=1.0)
        check_error_message(self, error, concept_type_error_message)

        with self.assertRaises(TypeError) as error:
            contextionary.extend(concept=some_concept["concept"], definition=None, weight=1.0)
        check_error_message(self, error, definition_type_error_message)

        with self.assertRaises(TypeError) as error:
            contextionary.extend(**some_concept, weight=None)
        check_error_message(self, error, weight_type_error_message)

        with self.assertRaises(ValueError) as error:
            contextionary.extend(**some_concept, weight=1.1)
        check_error_message(self, error, weight_value_error_message)

        with self.assertRaises(ValueError) as error:
            contextionary.extend(**some_concept, weight=-1.0)
        check_error_message(self, error, weight_value_error_message)

        ## test UnexpectedStatusCodeException
        contextionary = Contextionary(mock_connection_func("post", status_code=404))
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            contextionary.extend(**some_concept)
        check_startswith_error_message(self, error, unexpected_error_message)

        ## test requests error
        contextionary = Contextionary(
            mock_connection_func("post", side_effect=RequestsConnectionError("Test!"))
        )
        with self.assertRaises(RequestsConnectionError) as error:
            contextionary.extend(**some_concept)
        check_error_message(self, error, requests_error_message)

        ## test valid call without specifying 'weight'
        some_concept["weight"] = 1.0
        connection_mock = mock_connection_func("post", status_code=200)
        contextionary = Contextionary(connection_mock)
        contextionary.extend(**some_concept)
        connection_mock.post.assert_called_with(
            path="/modules/text2vec-contextionary/extensions",
            weaviate_object=some_concept,
        )

        ## test valid call with specifying 'weight as error'
        connection_mock = mock_connection_func("post", status_code=200)
        contextionary = Contextionary(connection_mock)
        # add weight to 'some_concept'
        some_concept["weight"] = 0.1234
        contextionary.extend(**some_concept)
        connection_mock.post.assert_called_with(
            path="/modules/text2vec-contextionary/extensions",
            weaviate_object=some_concept,
        )

    def test_get_concept_vector(self):
        """
        Test `get_concept_vector` method.
        """

        # test valid call
        connection_mock = mock_connection_func("get", return_json={"A": "B"})
        contextionary = Contextionary(connection_mock)
        self.assertEqual("B", contextionary.get_concept_vector("sauce")["A"])
        connection_mock.get.assert_called_with(
            path="/modules/text2vec-contextionary/concepts/sauce",
        )

        # test exceptions

        # error messages
        requests_error_message = "text2vec-contextionary vector was not retrieved."
        unexpected_exception_error_message = "text2vec-contextionary vector"

        ## test UnexpectedStatusCodeException
        contextionary = Contextionary(mock_connection_func("get", status_code=404))
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            contextionary.get_concept_vector("Palantir")
        check_startswith_error_message(self, error, unexpected_exception_error_message)

        ## test requests error
        contextionary = Contextionary(
            mock_connection_func("get", side_effect=RequestsConnectionError("Test!"))
        )
        with self.assertRaises(RequestsConnectionError) as error:
            contextionary.get_concept_vector("Palantir")
        check_error_message(self, error, requests_error_message)
