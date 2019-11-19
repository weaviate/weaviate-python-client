import unittest
import weaviate
from unittest.mock import Mock
from test.testing_util import add_run_rest_to_mock
from weaviate.connect import REST_METHOD_DELETE
from weaviate import UnexpectedStatusCodeException

class TestExceptions(unittest.TestCase):

    def test_unexpected_statuscode(self):
        w = weaviate.Client("http://localhost:8080")

        connection_mock = Mock()
        error = {
            "error": "Error message"
        }

        w.connection = add_run_rest_to_mock(connection_mock, status_code=404, return_json=error)

        try:
            w.delete_thing("b36268d4-a6b5-5274-985f-45f13ce0c642")
            self.fail("No unexpected status code")
        except UnexpectedStatusCodeException as e:
            self.assertEqual(e.status_code, 404)
            self.assertEqual(e.json, error)

    def test_unexpected_errror_json_none(self):
        w = weaviate.Client("http://localhost:8080")

        connection_mock = Mock()

        w.connection = add_run_rest_to_mock(connection_mock, status_code=404)

        try:
            w.delete_thing("b36268d4-a6b5-5274-985f-45f13ce0c642")
            self.fail("No unexpected status code")
        except UnexpectedStatusCodeException as e:
            self.assertEqual(e.status_code, 404)