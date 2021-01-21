import unittest
from unittest.mock import Mock
import weaviate
from weaviate import UnexpectedStatusCodeException
from weaviate.connect import REST_METHOD_DELETE
from test.util import replace_connection, add_run_rest_to_mock


class TestExceptions(unittest.TestCase):

    def test_unexpected_status_code_error(self):
        client = weaviate.Client("http://localhorst:8080")

        connection_mock = Mock()  # Mock calling weaviate
        error = {"error": "Error message"}
        add_run_rest_to_mock(connection_mock, status_code=404, return_json=error)
        replace_connection(client, connection_mock)

        try:
            client.data_object.delete("b36268d4-a6b5-5274-985f-45f13ce0c642")
        except UnexpectedStatusCodeException as e:
            self.assertEqual(e.status_code, 404)
            self.assertEqual(e.json, error)

        connection_mock.run_rest.assert_called()

        call_args_list = connection_mock.run_rest.call_args_list
        call_args = call_args_list[0][0]
        self.assertEqual(REST_METHOD_DELETE, call_args[1])

        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock, status_code=404)
        replace_connection(client, connection_mock)

        try:
            client.data_object.delete("b36268d4-a6b5-5274-985f-45f13ce0c642")
        except UnexpectedStatusCodeException as e:
            self.assertEqual(e.status_code, 404)
            self.assertIsNone(e.json)

        connection_mock.run_rest.assert_called()

        call_args_list = connection_mock.run_rest.call_args_list
        call_args = call_args_list[0][0]
        self.assertEqual(REST_METHOD_DELETE, call_args[1])