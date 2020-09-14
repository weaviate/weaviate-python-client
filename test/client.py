import unittest
import weaviate
from test.testing_util import *
from unittest.mock import Mock
from unittest.mock import patch


class TestWeaviateClient(unittest.TestCase):

    def test_create_weaviate_object_wrong_url(self):
        try:
            w = weaviate.Client(None)
            self.fail("No exception when no valid url given")
        except TypeError:
            pass  # Exception expected
        try:
            w = weaviate.Client(42)
            self.fail("No exception when no valid url given")
        except TypeError:
            pass  # Exception expected

    def test_create_weaviate_object_create_valid_object(self):
        try:
            w = weaviate.Client("http://localhost:8080")
        except Exception as e:
            self.fail("Unexpected exception: " + str(e))
        try:
            w = weaviate.Client("http://localhost:8080", "xyz")
        except Exception as e:
            self.fail("Unexpected exception: " + str(e))
        try:
            w = weaviate.Client("http://test.domain/path:8080", "xyz")
        except Exception as e:
            self.fail("Unexpected exception: " + str(e))
        try:
            w = weaviate.Client("http://hercules:8080", "xyz")
        except Exception as e:
            self.fail("Unexpected exception: " + str(e))
        with patch('weaviate.connect.connection.requests') as requests_mock:
            return_value_get_method = Mock()
            return_value_get_method.configure_mock(status_code=404)
            requests_mock.get.return_value = return_value_get_method
            try:
                w = weaviate.Client("http://35.205.175.0:80")
            except Exception as e:
                self.fail("Unexpected exception: " + str(e))

    def test_is_reachable(self):
        w = weaviate.Client("http://localhost:8080")
        connection_mock = Mock()
        # Request to weaviate returns 200
        w._connection = add_run_rest_to_mock(connection_mock)
        self.assertTrue(w.is_ready())  # Should be true

        # Test exception in connect
        w = weaviate.Client("http://localhost:8080")
        connection_mock = Mock()
        connection_mock.run_rest.side_effect = run_rest_raise_connection_error
        w._connection = connection_mock
        self.assertFalse(w.is_ready())

    def test_input_checking(self):
        w = weaviate.Client("http://localhost:8080/")
        self.assertEqual("http://localhost:8080/v1", w._connection.url, "Should remove trailing slash")

    def test_client_config(self):
        # The client config is supposed to just be a model.
        # The checking of the validity of the values should happen in the client.

        # Should work
        timeout = (3, 60)
        config = weaviate.ClientConfig(timeout_config=timeout)
        w = weaviate.Client("http://localhost:8080", client_config=config)
        self.assertEqual(timeout, w._connection.timeout_config)

        try:
            config = weaviate.ClientConfig(timeout_config="very long timeout")
            weaviate.Client("http://localhost:8080", client_config=config)
            self.fail("Should throw error")
        except TypeError:
            pass

        # Too long tupel
        try:
            config = weaviate.ClientConfig(timeout_config=(3, 4, 5))
            weaviate.Client("http://localhost:8080", client_config=config)
            self.fail("Should throw error")
        except ValueError:
            pass

        # tupel of wrong kind
        try:
            config = weaviate.ClientConfig(timeout_config=("many", "short"))
            weaviate.Client("http://localhost:8080", client_config=config)
            self.fail("Should throw error")
        except TypeError:
            pass


if __name__ == '__main__':
    unittest.main()
