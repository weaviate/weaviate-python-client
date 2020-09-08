import unittest
import weaviate
from test.testing_util import replace_connection, add_run_rest_to_mock
from weaviate import UnexpectedStatusCodeException
from unittest.mock import Mock
from weaviate.connect import REST_METHOD_DELETE


class TestExceptions(unittest.TestCase):

    def test_unexpected_statuscode(self):
        w = weaviate.Client("http://localhorst:8080")

        connection_mock = Mock()  # Mock calling weaviate
        error = {"error": "Error message"}
        add_run_rest_to_mock(connection_mock, status_code=404, return_json=error)
        replace_connection(w, connection_mock)

        try:
            w.data_object.delete("b36268d4-a6b5-5274-985f-45f13ce0c642")
            self.fail("No unexpected status code")
        except UnexpectedStatusCodeException as e:
            self.assertEqual(e.status_code, 404)
            self.assertEqual(e.json, error)

        connection_mock.run_rest.assert_called()

        call_args_list = connection_mock.run_rest.call_args_list
        call_args, call_kwargs = call_args_list[0]
        self.assertEqual(REST_METHOD_DELETE, call_args[1])

    def test_unexpected_errror_json_none(self):
        w = weaviate.Client("http://localhorst:8080")

        connection_mock = Mock()  # Mock calling weaviate
        add_run_rest_to_mock(connection_mock, status_code=404)
        replace_connection(w, connection_mock)

        try:
            w.data_object.delete("b36268d4-a6b5-5274-985f-45f13ce0c642")
            self.fail("No unexpected status code")
        except UnexpectedStatusCodeException as e:
            self.assertEqual(e.status_code, 404)

        connection_mock.run_rest.assert_called()

        call_args_list = connection_mock.run_rest.call_args_list
        call_args, call_kwargs = call_args_list[0]
        self.assertEqual(REST_METHOD_DELETE, call_args[1])