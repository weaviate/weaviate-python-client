import unittest
from unittest.mock import patch, Mock
import weaviate
from weaviate import Client
from weaviate.exceptions import RequestsConnectionError
from test.util import mock_run_rest, replace_connection, check_error_message
        

class TestWeaviateClient(unittest.TestCase):

    def test___init__(self):
        """
        Test the `__init__` method.
        """

        Client._connection = Mock()
        type_error_message = "URL is expected to be string but is "
        # test incalid calls
        with self.assertRaises(TypeError) as error:
            Client(None)
        check_error_message(self, error, type_error_message + str(type(None)))
        with self.assertRaises(TypeError) as error:
            Client(42)
        check_error_message(self, error, type_error_message + str(int))

        # test valid calls
        with patch('weaviate.client.Connection') as mock_obj:
            Client("some_URL", auth_client_secret=None, timeout_config=(1, 2))
            mock_obj.assert_called_with(
                url='some_URL',
                auth_client_secret=None,
                timeout_config=(1,2)
                )
        with patch('weaviate.client.Connection') as mock_obj:
            Client("some_URL/", auth_client_secret=None, timeout_config=(5, 20))
            mock_obj.assert_called_with(
                url='some_URL',
                auth_client_secret=None,
                timeout_config=(5,20)
                )


    def test_is_ready(self):
        """
        Test the `is_ready` method.
        """

        client = Client("http://localhost:8080")
        # Request to weaviate returns 200
        connection_mock = mock_run_rest()
        client._connection = connection_mock
        self.assertTrue(client.is_ready())  # Should be true
        connection_mock.run_rest.assert_called()
        connection_mock.run_rest.assert_called_with("/.well-known/ready", weaviate.connect.REST_METHOD_GET)

        # Request to weaviate returns 404
        connection_mock = mock_run_rest(status_code=404)
        client._connection = connection_mock
        self.assertFalse(client.is_ready())  # Should be false
        connection_mock.run_rest.assert_called()
        connection_mock.run_rest.assert_called_with("/.well-known/ready", weaviate.connect.REST_METHOD_GET)

        # Test exception in connect
        connection_mock = mock_run_rest(side_effect=RequestsConnectionError("Test"))
        client._connection = connection_mock
        self.assertFalse(client.is_ready())
        connection_mock.run_rest.assert_called()
        connection_mock.run_rest.assert_called_with("/.well-known/ready", weaviate.connect.REST_METHOD_GET)

    def test_is_live(self):
        """
        Test the `is_live` method.
        """

        client = Client("http://localhost:8080")
        # Request to weaviate returns 200
        connection_mock = mock_run_rest()
        client._connection = connection_mock
        self.assertTrue(client.is_live())  # Should be true
        connection_mock.run_rest.assert_called()
        connection_mock.run_rest.assert_called_with("/.well-known/live", weaviate.connect.REST_METHOD_GET)

        # Request to weaviate returns 404
        connection_mock = mock_run_rest(status_code=404)
        client._connection = connection_mock
        self.assertFalse(client.is_live())  # Should be false
        connection_mock.run_rest.assert_called()
        connection_mock.run_rest.assert_called_with("/.well-known/live", weaviate.connect.REST_METHOD_GET)

    def test_get_meta(self):
        """
        Test the `get_meta` method.
        """

        client = Client("http://localhost:8080")
        # Request to weaviate returns 200
        connection_mock = mock_run_rest(return_json="OK!")
        client._connection = connection_mock
        self.assertEqual(client.get_meta(), "OK!")
        connection_mock.run_rest.assert_called()
        connection_mock.run_rest.assert_called_with("/meta", weaviate.connect.REST_METHOD_GET)

        # Request to weaviate returns 404
        connection_mock = mock_run_rest(status_code=404)
        client._connection = connection_mock
        with self.assertRaises(weaviate.UnexpectedStatusCodeException) as error:
            client.get_meta()
        error_message = "Meta endpoint! Unexpected status code: 404, with response body: None"
        check_error_message(self, error, error_message)
        connection_mock.run_rest.assert_called()
        connection_mock.run_rest.assert_called_with("/meta", weaviate.connect.REST_METHOD_GET)
    
    def test_get_open_id_configuration(self):
        """
        Test the `get_open_id_configuration` method.
        """

        client = Client("http://localhost:8080")
        # Request to weaviate returns 200
        connection_mock = mock_run_rest(return_json="OK!")
        client._connection = connection_mock
        self.assertEqual(client.get_open_id_configuration(), "OK!")
        connection_mock.run_rest.assert_called()
        connection_mock.run_rest.assert_called_with("/.well-known/openid-configuration", weaviate.connect.REST_METHOD_GET)

        
        # Request to weaviate returns 404
        connection_mock = mock_run_rest(status_code=404)
        client._connection = connection_mock
        self.assertIsNone(client.get_open_id_configuration())
        connection_mock.run_rest.assert_called()
        connection_mock.run_rest.assert_called_with("/.well-known/openid-configuration", weaviate.connect.REST_METHOD_GET)

        # Request to weaviate returns 204
        connection_mock = mock_run_rest(status_code=204)
        client._connection = connection_mock
        with self.assertRaises(weaviate.UnexpectedStatusCodeException) as error:
            client.get_open_id_configuration()
        error_message = f"Meta endpoint! Unexpected status code: 204, with response body: None"
        check_error_message(self, error, error_message)
        connection_mock.run_rest.assert_called()
        connection_mock.run_rest.assert_called_with("/.well-known/openid-configuration", weaviate.connect.REST_METHOD_GET)

    def test_timeout_config(self):
        """
        Test the `set_timeout_config` method.
        """

        client = Client("some_URL", auth_client_secret=None, timeout_config=(1, 2))
        self.assertEqual(client.timeout_config, (1, 2))
        client.timeout_config = (4, 20) #;)
        self.assertEqual(client.timeout_config, (4, 20))
