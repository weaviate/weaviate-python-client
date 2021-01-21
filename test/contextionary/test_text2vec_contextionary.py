import unittest
from unittest.mock import Mock
import weaviate
from weaviate.connect import REST_METHOD_POST
from test.util import add_run_rest_to_mock, run_rest_raise_connection_error, replace_connection


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

        ## test exceptions
        with self.assertRaises(TypeError):
            client.contextionary.extend(concept=None, definition=some_concept["definition"], weight=1.0)
        with self.assertRaises(TypeError):
            client.contextionary.extend(concept=some_concept["concept"], definition=None, weight=1.0)
        with self.assertRaises(TypeError):
            client.contextionary.extend(**some_concept, weight=None)
        with self.assertRaises(ValueError):
            client.contextionary.extend(**some_concept, weight=1.1)
        with self.assertRaises(ValueError):
            client.contextionary.extend(**some_concept, weight=-1.0)

        ## test UnexpectedStatusCodeException
        with self.assertRaises(weaviate.UnexpectedStatusCodeException):
            connection_mock = Mock()
            connection_mock = add_run_rest_to_mock(connection_mock, status_code=404)
            replace_connection(client, connection_mock)
            client.contextionary.extend(**some_concept)

        ## test requests error
        with self.assertRaises(weaviate.RequestsConnectionError):
            connection_mock = Mock()  # Mock calling weaviate
            connection_mock.run_rest.side_effect = run_rest_raise_connection_error
            replace_connection(client, connection_mock)
            client.contextionary.extend(**some_concept)
        
        ## test valid call without specifying 'weight'
        connection_mock = Mock()  # Mock calling weaviate
        connection_mock = add_run_rest_to_mock(connection_mock, status_code=200)
        replace_connection(client, connection_mock)
        self.assertIsNone(client.contextionary.extend(**some_concept))
        connection_mock.run_rest.assert_called()
        call_args = connection_mock.run_rest.call_args_list[0][0]
        self.assertEqual("/modules/text2vec-contextionary/extensions", call_args[0])
        self.assertEqual(weaviate.connect.REST_METHOD_POST, call_args[1])
        some_concept["weight"] = 1.0
        self.assertEqual(some_concept, call_args[2])

        ## test valid call with specifying 'weight'
        connection_mock = Mock()  # Mock calling weaviate
        connection_mock = add_run_rest_to_mock(connection_mock, status_code=200)
        replace_connection(client, connection_mock)
        # add weigth to 'some_concept'
        some_concept["weight"] = .1234
        self.assertIsNone(client.contextionary.extend(**some_concept))
        connection_mock.run_rest.assert_called()
        call_args = connection_mock.run_rest.call_args_list[0][0]
        self.assertEqual("/modules/text2vec-contextionary/extensions", call_args[0])
        self.assertEqual(weaviate.connect.REST_METHOD_POST, call_args[1])
        self.assertEqual(some_concept, call_args[2])

    def test_get_concept_vector(self):
        """
        Test `get_concept_vector` method.
        """

        client = weaviate.Client("http://citadelofricks.city:6969")

        # test valid call
        connection_mock = Mock()
        connection_mock = add_run_rest_to_mock(connection_mock, return_json={"A": "B"})
        replace_connection(client, connection_mock)
        self.assertEqual("B", client.contextionary.get_concept_vector("sauce")["A"])

        # test exceptions
        ## test UnexpectedStatusCodeException
        with self.assertRaises(weaviate.UnexpectedStatusCodeException):
            connection_mock = Mock()
            connection_mock = add_run_rest_to_mock(connection_mock, status_code=404)
            replace_connection(client, connection_mock)
            client.contextionary.get_concept_vector("Palantir")
        ## test requests error
        with self.assertRaises(weaviate.RequestsConnectionError):
            connection_mock = Mock()  # Mock calling weaviate
            connection_mock.run_rest.side_effect = run_rest_raise_connection_error
            replace_connection(client, connection_mock)
            client.contextionary.get_concept_vector("Palantir")
