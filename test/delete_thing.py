import unittest
import weaviate
from unittest.mock import Mock
from test.testing_util import add_run_rest_to_mock
from weaviate.connect import REST_METHOD_DELETE
from weaviate import UnexpectedStatusCodeException

class TestDeleteThings(unittest.TestCase):

    def test_function_input(self):
        w = weaviate.Client("http://localhost:8080")
        try:
            w.delete_thing(4)
            self.fail("UUID has the wrong type")
        except TypeError:
            pass

        try:
            w.delete_thing("Hallo Wereld")
            self.fail("UUID has the wrong value")
        except ValueError:
            pass

    def test_delete_thing(self):
        w = weaviate.Client("http://localhost:8080")

        # 1. Succesfully delete something
        connection_mock = Mock()
        w.connection = add_run_rest_to_mock(connection_mock, status_code=204)

        thing = "b36268d4-a6b5-5274-985f-45f13ce0c642"
        w.delete_thing(thing)

        connection_mock.run_rest.assert_called_with("/things/"+thing, REST_METHOD_DELETE)

        # 2. Delete something that does not exist
        connection_mock = Mock()
        w.connection = add_run_rest_to_mock(connection_mock, status_code=404)

        thing = "b36268d4-a6b5-5274-985f-45f13ce0c642"
        try:
            w.delete_thing(thing)
            self.fail("Unexpected status code")
        except UnexpectedStatusCodeException:
            pass

        connection_mock.run_rest.assert_called_with("/things/" + thing, REST_METHOD_DELETE)
