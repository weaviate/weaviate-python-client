import unittest
from unittest.mock import patch, Mock
from weaviate import Client
from weaviate.exceptions import RequestsConnectionError, UnexpectedStatusCodeException
from test.util import mock_connection_method, check_error_message



@patch('weaviate.client.Connection', Mock)
class TestWeaviateClient(unittest.TestCase):


    def test___init__(self):
        """
        Test the `__init__` method.
        """

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
        connection_mock = mock_connection_method('get')
        client._connection = connection_mock
        self.assertTrue(client.is_ready())  # Should be true
        connection_mock.get.assert_called_with(
            path="/.well-known/ready"
        )

        # Request to weaviate returns 404
        connection_mock = mock_connection_method('get', status_code=404)
        client._connection = connection_mock
        self.assertFalse(client.is_ready())  # Should be false
        connection_mock.get.assert_called_with(
            path="/.well-known/ready"
        )

        # Test exception in connect
        connection_mock = mock_connection_method('get', side_effect=RequestsConnectionError("Test"))
        client._connection = connection_mock
        self.assertFalse(client.is_ready())
        connection_mock.get.assert_called_with(
            path="/.well-known/ready"
        )

    def test_is_live(self):
        """
        Test the `is_live` method.
        """

        client = Client("http://localhost:8080")
        # Request to weaviate returns 200
        connection_mock = mock_connection_method('get')
        client._connection = connection_mock
        self.assertTrue(client.is_live())  # Should be true
        connection_mock.get.assert_called_with(
            path="/.well-known/live"
        )

        # Request to weaviate returns 404
        connection_mock = mock_connection_method('get', status_code=404)
        client._connection = connection_mock
        self.assertFalse(client.is_live())  # Should be false
        connection_mock.get.assert_called_with(
            path="/.well-known/live"
        )

    def test_get_meta(self):
        """
        Test the `get_meta` method.
        """

        client = Client("http://localhost:8080")
        # Request to weaviate returns 200
        connection_mock = mock_connection_method('get',return_json="OK!")
        client._connection = connection_mock
        self.assertEqual(client.get_meta(), "OK!")
        connection_mock.get.assert_called_with(
            path="/meta"
        )

        # Request to weaviate returns 404
        connection_mock = mock_connection_method('get', status_code=404)
        client._connection = connection_mock
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            client.get_meta()
        error_message = "Meta endpoint! Unexpected status code: 404, with response body: None"
        check_error_message(self, error, error_message)
        connection_mock.get.assert_called_with(
            path="/meta"
        )

    def test_get_open_id_configuration(self):
        """
        Test the `get_open_id_configuration` method.
        """

        client = Client("http://localhost:8080")
        # Request to weaviate returns 200
        connection_mock = mock_connection_method('get', return_json="OK!")
        client._connection = connection_mock
        self.assertEqual(client.get_open_id_configuration(), "OK!")
        connection_mock.get.assert_called_with(
            path="/.well-known/openid-configuration"
        )

        
        # Request to weaviate returns 404
        connection_mock = mock_connection_method('get', status_code=404)
        client._connection = connection_mock
        self.assertIsNone(client.get_open_id_configuration())
        connection_mock.get.assert_called_with(
            path="/.well-known/openid-configuration"
        )

        # Request to weaviate returns 204
        connection_mock = mock_connection_method('get', status_code=204)
        client._connection = connection_mock
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            client.get_open_id_configuration()
        error_message = f"Meta endpoint! Unexpected status code: 204, with response body: None"
        check_error_message(self, error, error_message)
        connection_mock.get.assert_called_with(
            path="/.well-known/openid-configuration"
        )

    def test_timeout_config(self):
        """
        Test the `set_timeout_config` method.
        """

        client = Client("http://some_url.com", auth_client_secret=None, timeout_config=(1, 2))
        self.assertEqual(client.timeout_config, (1, 2))
        client.timeout_config = (4, 20) #;)
        self.assertEqual(client.timeout_config, (4, 20))
