import unittest
import weaviate
from test.testing_util import replace_connection, add_run_rest_to_mock, Mock
from weaviate.connect import REST_METHOD_POST


class TestQuery(unittest.TestCase):
    
    def setUp(self):
        self.client = weaviate.Client("http://localhorst:8080")

    def test_get(self):
        gql = self.client.query.get("Group", ["name", "uuid"]).build()
        self.assertEqual("{Get{Group{name uuid}}}", gql)

    def test_aggregate(self):
        gql = self.client.query.aggregate("Group").build()
        self.assertEqual("{Aggregate{Group{}}}", gql)

    def test_raw(self):

        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock)
        replace_connection(self.client, connection_mock)

        query = "{Get {Group {name Members {... on Person {name}}}}}"
        self.client.query.raw(query)

        connection_mock.run_rest.assert_called()
        connection_mock.run_rest.assert_called_with("/graphql", REST_METHOD_POST, {"query": query})

    def test_do(self):

        return_value = {
            "data": {
                "Get": {
                    "Group": [
                        {
                            "name": "Legends",
                            "uuid": "2db436b5-0557-5016-9c5f-531412adf9c6"
                        }
                    ]
                }
            },
            "errors": None
        }

        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock, return_value)
        replace_connection(self.client, connection_mock)
        # Mock Things object in Query class


        response = self.client.query.get("Group", ["name", "uuid"]).do()

        self.assertEqual(return_value, response)

        connection_mock.run_rest.assert_called()
        connection_mock.run_rest.assert_called_with("/graphql", REST_METHOD_POST, {"query": "{Get{Group{name uuid}}}"})
