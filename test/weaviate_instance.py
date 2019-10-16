import unittest
import weaviate
from test.testing_util import *
from unittest.mock import Mock

class TestWeaviate(unittest.TestCase):
    def test_create_weaviate_object_wrong_url(self):
        try:
            w = weaviate.Weaviate(None)
            self.fail("No exception when no valid url given")
        except TypeError:
            pass  # Exception expected
        try:
            w = weaviate.Weaviate(42)
            self.fail("No exception when no valid url given")
        except TypeError:
            pass  # Exception expected
        try:
            w = weaviate.Weaviate("")
            self.fail("No exception when no valid url given")
        except ValueError:
            pass  # Exception expected
        try:
            w = weaviate.Weaviate("hallo\tasdf")
            self.fail("No exception when no valid url given")
        except ValueError:
            pass  # Exception expected

    def test_create_weaviate_object_create_valid_object(self):
        try:
            w = weaviate.Weaviate("http://localhost:8080")
        except Exception as e:
            self.fail("Unexpected exception: " + str(e))
        try:
            w = weaviate.Weaviate("http://localhost:8080", "xyz")
        except Exception as e:
            self.fail("Unexpected exception: " + str(e))
        try:
            w = weaviate.Weaviate("http://test.domain/path:8080", "xyz")
        except Exception as e:
            self.fail("Unexpected exception: " + str(e))

    def test_is_reachable(self):
        w = weaviate.Weaviate("http://localhost:8080")
        connection_mock = Mock()
        # Request to weaviate returns 200
        w.connection = add_run_rest_to_mock(connection_mock)
        self.assertTrue(w.is_reachable())  # Should be true

        # Test exception in connect
        w = weaviate.Weaviate("http://localhost:8080")
        connection_mock = Mock()
        connection_mock.run_rest.side_effect = run_rest_raise_connection_error
        w.connection = connection_mock
        self.assertFalse(w.is_reachable())



if __name__ == '__main__':
    unittest.main()
