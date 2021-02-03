import unittest
import weaviate
from weaviate.exceptions import RequestsConnectionError, UnexpectedStatusCodeException
from weaviate.connect import REST_METHOD_POST
from test.util import replace_connection, mock_run_rest, check_error_message, check_startswith_error_message


class TestQuery(unittest.TestCase):
    
    def setUp(self):
        self.client = weaviate.Client("http://localhorst:8080")

    def test_get(self):
        """
        Test the `get` attribute.
        """

        gql = self.client.query.get("Group", ["name", "uuid"]).build()
        self.assertEqual("{Get{Group{name uuid}}}", gql)

    def test_aggregate(self):
        """
        Test the `aggregate` attribute.
        """

        gql = self.client.query.aggregate("Group").build()
        self.assertEqual("{Aggregate{Group{}}}", gql)

    def test_raw(self):
        """
        Test the `raw` method.
        """

        # valid calls
        connection_mock = mock_run_rest()
        replace_connection(self.client, connection_mock)

        query = "{Get {Group {name Members {... on Person {name}}}}}"
        self.client.query.raw(query)

        connection_mock.run_rest.assert_called()
        connection_mock.run_rest.assert_called_with("/graphql", REST_METHOD_POST, {"query": query})

        # invalid calls
        
        type_error_message = "Query is expected to be a string"
        requests_error_message = 'Test! Connection error, query not executed.'
        query_error_message = "GQL query failed"

        with self.assertRaises(TypeError) as error:
            self.client.query.raw(["TestQuery"])
        check_error_message(self, error, type_error_message)

        replace_connection(self.client, mock_run_rest(side_effect=RequestsConnectionError("Test!")))
        with self.assertRaises(RequestsConnectionError) as error:
            self.client.query.raw("TestQuery")
        check_error_message(self, error, requests_error_message)

        replace_connection(self.client, mock_run_rest(status_code=404))
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            self.client.query.raw("TestQuery")
        check_startswith_error_message(self, error, query_error_message)
