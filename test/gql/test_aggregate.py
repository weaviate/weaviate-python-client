import unittest
from unittest.mock import Mock
import weaviate
from weaviate.gql.aggregate import AggregateBuilder
from weaviate.exceptions import RequestsConnectionError
from test.util import mock_run_rest, replace_connection, check_error_message, check_startswith_error_message


class TestAggregateBuilder(unittest.TestCase):

    def setUp(self):

        self.aggregate = AggregateBuilder("Object", None)

    def test_with_meta_count(self):
        """
        Test the `with_meta_count` method.
        """

        query = self.aggregate\
            .with_meta_count()\
            .build()
        self.assertEqual("{Aggregate{Object{meta{count}}}}", query)

    def test_with_fields(self):
        """
        Test the `with_fields` method.
        """

        query = self.aggregate \
            .with_fields("size { mean }") \
            .build()
        self.assertEqual("{Aggregate{Object{size { mean }}}}", query)

    def test_with_where(self):
        """
        Test the `with_where` method.
        """

        filter = {
            "operator": "Equal",
            "valueString": "B",
            "path": ["name"]
        }

        query = self.aggregate\
            .with_meta_count()\
            .with_where(filter)\
            .build()
        self.assertEqual('{Aggregate{Object(where: {path: ["name"] operator: Equal valueString: "B"} ){meta{count}}}}', query)

    def test_group_by_filter(self):
        """
        Test the `with_group_by_filter` method.
        """

        query = self.aggregate\
            .with_group_by_filter(["name"])\
            .with_fields("groupedBy { value }")\
            .with_fields("name { count }")\
            .build()
        self.assertEqual('{Aggregate{Object(groupBy: ["name"]){groupedBy { value }name { count }}}}', query)

    def test_do(self):
        """
        Test the `do` method.
        """

        # test exceptions
        requests_error_message ='Test Connection error, query was not successful.'

        # requests.exceptions.ConnectionError
        mock_obj = mock_run_rest(side_effect=RequestsConnectionError("Test"))
        self.aggregate._connection = mock_obj
        with self.assertRaises(weaviate.RequestsConnectionError) as error:            
            self.aggregate.do()
        check_error_message(self, error, requests_error_message)

        # weaviate.UnexpectedStatusCodeException
        mock_obj = mock_run_rest(status_code=204)
        self.aggregate._connection = mock_obj
        with self.assertRaises(weaviate.UnexpectedStatusCodeException) as error:
            self.aggregate.do()
        check_startswith_error_message(self, error, "Query was not successful")


        filter = {
          "path": ["name"],
          "operator": "Equal",
          "valueString": "B"
        }

        self.aggregate \
            .with_group_by_filter(["name"]) \
            .with_fields("groupedBy { value }") \
            .with_fields("name { count }") \
            .with_where(filter)
        expected_gql_clause = '{Aggregate{Object(where: {path: ["name"] operator: Equal valueString: "B"} groupBy: ["name"]){groupedBy { value }name { count }}}}'

        mock_obj = mock_run_rest(status_code=200, return_json={"status": "OK!"})
        self.aggregate._connection = mock_obj
        self.assertEqual(self.aggregate.do(), {"status": "OK!"})
        mock_obj.run_rest.assert_called_with(
            "/graphql",
            weaviate.connect.REST_METHOD_POST,
            {'query' : expected_gql_clause})
