import unittest
import weaviate
from test.testing_util import add_run_rest_to_mock, replace_connection
from weaviate.connect import REST_METHOD_DELETE
from weaviate import UnexpectedStatusCodeException
import sys
if sys.version_info[0] == 2:
    from mock import MagicMock as Mock
else:
    from unittest.mock import Mock


class TestDelete(unittest.TestCase):

    def test_delete_thing_input(self):
        w = weaviate.Client("http://localhost:8080")
        try:
            w.data_object.delete(4)
            self.fail("UUID has the wrong type")
        except TypeError:
            pass

        try:
            w.data_object.delete("Hallo Wereld")
            self.fail("UUID has the wrong value")
        except ValueError:
            pass

    def test_delete_thing(self):
        w = weaviate.Client("http://localhost:8080")

        # 1. Succesfully delete something
        connection_mock = Mock()
        add_run_rest_to_mock(connection_mock, status_code=204)
        replace_connection(w, connection_mock)

        thing = "b36268d4-a6b5-5274-985f-45f13ce0c642"
        w.data_object.delete(thing)

        connection_mock.run_rest.assert_called_with("/things/"+thing, REST_METHOD_DELETE)

        # 2. Delete something that does not exist
        connection_mock = Mock()
        add_run_rest_to_mock(connection_mock, status_code=404)
        replace_connection(w, connection_mock)

        thing = "b36268d4-a6b5-5274-985f-45f13ce0c642"
        try:
            w.data_object.delete(thing)
            self.fail("Unexpected status code")
        except UnexpectedStatusCodeException:
            pass

        connection_mock.run_rest.assert_called_with("/things/" + thing, REST_METHOD_DELETE)

    def test_get_thing(self):
        w = weaviate.Client("http://localhost:8080")

        thing = {
            "name": "test"
        }
        connection_mock = Mock()
        add_run_rest_to_mock(connection_mock, return_json=thing, status_code=200)
        replace_connection(w, connection_mock)

        result = w.data_object.get("73802305-c0da-427e-b21c-d6779a22f35f")
        self.assertIn("name", result)
