import unittest
import weaviate
from test.testing_util import *
from unittest.mock import Mock
from unittest.mock import patch

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
        with patch('weaviate.connect.connection.requests') as requests_mock:
            return_value_get_method = Mock()
            return_value_get_method.configure_mock(status_code=404)
            requests_mock.get.return_value = return_value_get_method
            try:
                w = weaviate.Weaviate("http://35.205.175.0:80")
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
