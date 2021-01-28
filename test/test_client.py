import unittest
from unittest.mock import patch, Mock
import weaviate
from weaviate import ClientConfig, Client
from weaviate.exceptions import RequestsConnectionError
from test.util import mock_run_rest, replace_connection


class TestWeaviateClientConfig(unittest.TestCase):

    def test___init__(self):
        """
        Test the `__init__` method.
        """

        # valid arguments
        self.assertEqual(ClientConfig((1, 2)).timeout_config, (1, 2))
        self.assertEqual(ClientConfig([1, 2]).timeout_config, (1, 2))

        # invalid arguments
        with self.assertRaises(TypeError):
            ClientConfig((1., 2))
        with self.assertRaises(TypeError):
            ClientConfig((1, 2.))
        with self.assertRaises(TypeError):
            ClientConfig({1, 2})
        with self.assertRaises(ValueError):
            ClientConfig((1, 2, 3))
        with self.assertRaises(ValueError):
            ClientConfig([1])
        

class TestWeaviateClient(unittest.TestCase):

    def test___init__(self):
        """
        Test the `__init__` method.
        """

        Client._connection = Mock()
        # test incalid calls
        with self.assertRaises(TypeError):
            Client(None)
        with self.assertRaises(TypeError):
            Client(42)

        # test valid calls
        with patch('weaviate.client.Connection') as mock_obj:
            Client("some_URL", auth_client_secret=None, client_config=ClientConfig((1, 2)))
            mock_obj.assert_called_with(
                url='some_URL',
                auth_client_secret=None,
                timeout_config=(1,2)
                )
        with patch('weaviate.client.Connection') as mock_obj:
            Client("some_URL/", auth_client_secret=None, client_config=ClientConfig((5, 20)))
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
        with self.assertRaises(weaviate.UnexpectedStatusCodeException):
            client.get_meta()
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
        with self.assertRaises(weaviate.UnexpectedStatusCodeException):
            client.get_open_id_configuration()
        connection_mock.run_rest.assert_called()
        connection_mock.run_rest.assert_called_with("/.well-known/openid-configuration", weaviate.connect.REST_METHOD_GET)
