import unittest
from unittest.mock import Mock

from requests.exceptions import ConnectionError as RequestsConnectionError

from test.util import mock_connection_func, check_error_message, check_startswith_error_message
from weaviate.exceptions import UnexpectedStatusCodeException
from weaviate.gql.query import Query


class TestQuery(unittest.TestCase):
    def test_get(self):
        """
        Test the `get` attribute.
        """

        query = Query(Mock())

        gql = query.get("Group", ["name", "uuid"]).build()
        self.assertEqual("{Get{Group{name uuid}}}", gql)

    def test_aggregate(self):
        """
        Test the `aggregate` attribute.
        """

        query = Query(Mock())

        gql = query.aggregate("Group").build()
        self.assertEqual("{Aggregate{Group{}}}", gql)

    def test_raw(self):
        """
        Test the `raw` method.
        """

        # valid calls
        connection_mock = mock_connection_func("post", return_json={})
        query = Query(connection_mock)

        gql_query = "{Get {Group {name Members {... on Person {name}}}}}"
        query.raw(gql_query)

        connection_mock.post.assert_called_with(
            path="/graphql", weaviate_object={"query": gql_query}
        )

        # invalid calls

        type_error_message = "Query is expected to be a string"
        requests_error_message = "Query not executed."
        query_error_message = "GQL query failed"

        with self.assertRaises(TypeError) as error:
            query.raw(["TestQuery"])
        check_error_message(self, error, type_error_message)

        query = Query(mock_connection_func("post", side_effect=RequestsConnectionError("Test!")))
        with self.assertRaises(RequestsConnectionError) as error:
            query.raw("TestQuery")
        check_error_message(self, error, requests_error_message)

        query = Query(mock_connection_func("post", status_code=404))
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            query.raw("TestQuery")
        check_startswith_error_message(self, error, query_error_message)
