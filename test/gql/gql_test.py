import unittest
import weaviate
from weaviate.gql.query import Things
from test.testing_util import replace_connection, add_run_rest_to_mock
from unittest.mock import Mock
from weaviate.connect import REST_METHOD_POST


class TestGraphQL(unittest.TestCase):

    def test_get(self):
        w = weaviate.Client("http://localhorst:8080")
        gql = w.query.get.things("Group", ["name", "uuid"]).build()
        self.assertEqual("{Get{Things{Group{name uuid}}}}", gql)

    def test_raw(self):
        w = weaviate.Client("http://localhorst:8080")

        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock)
        replace_connection(w, connection_mock)

        query = "{Get {Things {Group {name Members {... on Person {name}}}}}}"
        w.query.raw(query)

        connection_mock.run_rest.assert_called()

        call_args_list = connection_mock.run_rest.call_args_list
        call_args, call_kwargs = call_args_list[0]

        self.assertEqual("/graphql", call_args[0])
        self.assertEqual(REST_METHOD_POST, call_args[1])
        self.assertEqual({"query": query}, call_args[2])

    def test_do(self):
        w = weaviate.Client("http://localhorst:8080")

        return_value = {
            "data": {
                "Get": {
                    "Things": {
                        "Group": [
                            {
                                "name": "Legends",
                                "uuid": "2db436b5-0557-5016-9c5f-531412adf9c6"
                            }
                        ]
                    }
                }
            },
            "errors": None
        }

        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock, return_value)
        replace_connection(w, connection_mock)
        # Mock Things object in Query class
        w.query.get = Things(connection_mock)

        response = w.query.get.things("Group", ["name", "uuid"]).do()

        self.assertEqual(return_value, response)

        connection_mock.run_rest.assert_called()
        call_args_list = connection_mock.run_rest.call_args_list

        call_args, call_kwargs = call_args_list[0]
        self.assertEqual("/graphql", call_args[0])
        self.assertEqual(REST_METHOD_POST, call_args[1])
        self.assertEqual({"query": "{Get{Things{Group{name uuid}}}}"}, call_args[2])