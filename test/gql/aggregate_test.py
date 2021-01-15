import unittest
import weaviate
from weaviate.gql.aggregate import AggregateBuilder
from test.testing_util import Mock, add_run_rest_to_mock, run_rest_raise_connection_error, replace_connection


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
        # requests.exceptions.ConnectionError
        with self.assertRaises(weaviate.RequestsConnectionError):
            mock_obj = Mock()
            mock_obj.run_rest.side_effect = run_rest_raise_connection_error
            self.aggregate._connection = mock_obj
            self.aggregate.do()
        # weaviate.UnexpectedStatusCodeException
        with self.assertRaises(weaviate.UnexpectedStatusCodeException):
            mock_obj = Mock()
            add_run_rest_to_mock(mock_obj, status_code=204)
            self.aggregate._connection = mock_obj
            self.aggregate.do()


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

        mock_obj = Mock()
        add_run_rest_to_mock(mock_obj, status_code=200, return_json={"status": "OK!"})
        self.aggregate._connection = mock_obj
        self.assertEquals(self.aggregate.do(), {"status": "OK!"})
        mock_obj.run_rest.assert_called()
        mock_obj.run_rest.assert_called_with(
            "/graphql",
            weaviate.connect.REST_METHOD_POST,
            {'query' : expected_gql_clause})
