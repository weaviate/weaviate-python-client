import unittest
import weaviate
from test.testing_util import add_run_rest_to_mock
import sys
if sys.version_info[0] == 2:
    from mock import MagicMock as Mock
else:
    from unittest.mock import Mock


class TestPatchThing(unittest.TestCase):
    def test_patch_thing_wrong_input(self):
        w = weaviate.Client("http://localhost:8080")
        try:
            w.patch_thing(None, "Class", "ae6d51d6-b4ea-5a03-a808-6aae990bdebf")
            self.fail("Thing was not given but accepted anyways")
        except TypeError:
            pass
        try:
            w.patch_thing({"A": "B"}, 35, "ae6d51d6-b4ea-5a03-a808-6aae990bdebf")
            self.fail("Class is not string")
        except TypeError:
            pass
        try:
            w.patch_thing({"A": "B"}, "Class", 1238234)
            self.fail("Class is not string")
        except TypeError:
            pass
        try:
            w.patch_thing({"A": "B"}, "Class", "NOT-A-valid-uuid")
            self.fail("Class is not string")
        except ValueError:
            pass

    def test_patch_thing(self):
        # Run a successful request
        w = weaviate.Client("http://localhost:8080")
        connection_mock = Mock()
        w._connection = add_run_rest_to_mock(connection_mock, status_code=204)

        x = w.patch_thing({"A": "B"}, "Class", "ae6d51d6-b4ea-5a03-a808-6aae990bdebf")

        self.assertEqual(x, None)
        connection_mock.run_rest.assert_called()

        # Run a request with unexpected status code
        connection_mock = Mock()
        w._connection = add_run_rest_to_mock(connection_mock, status_code=404)

        try:
            w.patch_thing({"A": "B"}, "Class", "ae6d51d6-b4ea-5a03-a808-6aae990bdebf")
            self.fail("No exception was thrown")
        except weaviate.UnexpectedStatusCodeException:
            pass
        connection_mock.run_rest.assert_called()
