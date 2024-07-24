import unittest
from sys import platform
from unittest.mock import patch, Mock

from requests.exceptions import ConnectionError as RequestsConnectionError

from test.util import mock_connection_func, check_error_message
from weaviate import Client
from weaviate.config import ConnectionConfig
from weaviate.embedded import EmbeddedOptions, EmbeddedDB
from weaviate.exceptions import UnexpectedStatusCodeException


@patch("weaviate.client.Connection", Mock)
class TestWeaviateClient(unittest.TestCase):
    @patch("weaviate.client.Client.get_meta", return_value={"version": "1.13.2"})
    def test___init__(self, mock_get_meta_method):
        """
        Test the `__init__` method.
        """

        type_error_message = "Either url or embedded options must be present."
        # test invalid calls
        with self.assertRaises(TypeError) as error:
            Client(None)
        check_error_message(self, error, type_error_message)
        with self.assertRaises(TypeError) as error:
            Client(42)
        check_error_message(self, error, "URL is expected to be string but is " + str(int))

        # test valid calls
        with patch(
            "weaviate.client.Connection",
            Mock(side_effect=lambda **kwargs: Mock(timeout_config=kwargs["timeout_config"])),
        ) as mock_obj:
            Client(
                url="some_URL",
                auth_client_secret=None,
                timeout_config=(1, 2),
                additional_headers=None,
                startup_period=None,
            )
            mock_obj.assert_called_with(
                url="some_URL",
                auth_client_secret=None,
                timeout_config=(1, 2),
                proxies=None,
                trust_env=False,
                additional_headers=None,
                startup_period=None,
                embedded_db=None,
                grcp_port=None,
                connection_config=ConnectionConfig(),
            )

        with patch(
            "weaviate.client.Connection",
            Mock(side_effect=lambda **kwargs: Mock(timeout_config=kwargs["timeout_config"])),
        ) as mock_obj:
            Client(
                url="some_URL",
                auth_client_secret=None,
                timeout_config=(1, 2),
                additional_headers={"Test": True},
                startup_period=None,
            )
            mock_obj.assert_called_with(
                url="some_URL",
                auth_client_secret=None,
                timeout_config=(1, 2),
                proxies=None,
                trust_env=False,
                additional_headers={"Test": True},
                startup_period=None,
                embedded_db=None,
                grcp_port=None,
                connection_config=ConnectionConfig(),
            )

        with patch(
            "weaviate.client.Connection",
            Mock(side_effect=lambda **kwargs: Mock(timeout_config=kwargs["timeout_config"])),
        ) as mock_obj:
            Client(
                "some_URL/", auth_client_secret=None, timeout_config=(5, 20), startup_period=None
            )
            mock_obj.assert_called_with(
                url="some_URL",
                auth_client_secret=None,
                timeout_config=(5, 20),
                proxies=None,
                trust_env=False,
                additional_headers=None,
                startup_period=None,
                embedded_db=None,
                grcp_port=None,
                connection_config=ConnectionConfig(),
            )

        with patch(
            "weaviate.client.Connection",
            Mock(side_effect=lambda **kwargs: Mock(timeout_config=kwargs["timeout_config"])),
        ) as mock_obj:
            Client(
                url="some_URL",
                auth_client_secret=None,
                timeout_config=(1, 2),
                proxies={"http": "test"},
                trust_env=True,
                additional_headers=None,
                startup_period=None,
            )
            mock_obj.assert_called_with(
                url="some_URL",
                auth_client_secret=None,
                timeout_config=(1, 2),
                proxies={"http": "test"},
                trust_env=True,
                additional_headers=None,
                startup_period=None,
                embedded_db=None,
                grcp_port=None,
                connection_config=ConnectionConfig(),
            )

        if platform == "linux":
            with patch(
                "weaviate.client.Connection",
                Mock(side_effect=lambda **kwargs: Mock(timeout_config=kwargs["timeout_config"])),
            ) as mock_obj:
                with patch("weaviate.embedded.EmbeddedDB.start") as mocked_start:
                    Client(embedded_options=EmbeddedOptions())
                    args, kwargs = mock_obj.call_args_list[0]
                    self.assertEqual(kwargs["url"], "http://localhost:8079")
                    self.assertTrue(isinstance(kwargs["embedded_db"], EmbeddedDB))
                    self.assertTrue(kwargs["embedded_db"] is not None)
                    self.assertEqual(kwargs["embedded_db"].options.port, 8079)
                    mocked_start.assert_called_once()

    @patch("weaviate.client.Client.get_meta", return_value={"version": "1.13.2"})
    def test_is_ready(self, mock_get_meta_method):
        """
        Test the `is_ready` method.
        """

        client = Client("http://localhost:8080")
        # Request to weaviate returns 200
        connection_mock = mock_connection_func("get")
        client._connection = connection_mock
        self.assertTrue(client.is_ready())  # Should be true
        connection_mock.get.assert_called_with(path="/.well-known/ready")

        # Request to weaviate returns 404
        connection_mock = mock_connection_func("get", status_code=404)
        client._connection = connection_mock
        self.assertFalse(client.is_ready())  # Should be false
        connection_mock.get.assert_called_with(path="/.well-known/ready")

        # Test exception in connect
        connection_mock = mock_connection_func("get", side_effect=RequestsConnectionError("Test"))
        client._connection = connection_mock
        self.assertFalse(client.is_ready())
        connection_mock.get.assert_called_with(path="/.well-known/ready")

    @patch("weaviate.client.Client.get_meta", return_value={"version": "1.13.2"})
    def test_is_live(self, mock_get_meta):
        """
        Test the `is_live` method.
        """

        client = Client("http://localhost:8080")
        # Request to weaviate returns 200
        connection_mock = mock_connection_func("get")
        client._connection = connection_mock
        self.assertTrue(client.is_live())  # Should be true
        connection_mock.get.assert_called_with(path="/.well-known/live")

        # Request to weaviate returns 404
        connection_mock = mock_connection_func("get", status_code=404)
        client._connection = connection_mock
        self.assertFalse(client.is_live())  # Should be false
        connection_mock.get.assert_called_with(path="/.well-known/live")

    def test_get_meta(self):
        """
        Test the `get_meta` method.
        """

        # client = Client("http://localhost:8080")
        # # Request to weaviate returns 200
        # connection_mock = mock_connection_func('get', return_json="OK!")
        # client._connection = connection_mock
        # self.assertEqual(client.get_meta(), "OK!")
        # connection_mock.get.assert_called_with(
        #     path="/meta"
        # )

        # # Request to weaviate returns 404
        # connection_mock = mock_connection_func('get', status_code=404)
        # client._connection = connection_mock
        # with self.assertRaises(UnexpectedStatusCodeException) as error:
        #     client.get_meta()
        # error_message = "Meta endpoint! Unexpected status code: 404, with response body: None"
        # check_error_message(self, error, error_message)
        # connection_mock.get.assert_called_with(
        #     path="/meta"
        # )

    @patch("weaviate.client.Client.get_meta", return_value={"version": "1.13.2"})
    def test_get_open_id_configuration(self, mock_get_meta):
        """
        Test the `get_open_id_configuration` method.
        """

        client = Client("http://localhost:8080")
        # Request to weaviate returns 200
        connection_mock = mock_connection_func("get", return_json={"status": "OK!"})
        client._connection = connection_mock
        self.assertEqual(client.get_open_id_configuration(), {"status": "OK!"})
        connection_mock.get.assert_called_with(path="/.well-known/openid-configuration")

        # Request to weaviate returns 404
        connection_mock = mock_connection_func("get", status_code=404)
        client._connection = connection_mock
        self.assertIsNone(client.get_open_id_configuration())
        connection_mock.get.assert_called_with(path="/.well-known/openid-configuration")

        # Request to weaviate returns 204
        connection_mock = mock_connection_func("get", status_code=204)
        client._connection = connection_mock
        with self.assertRaises(UnexpectedStatusCodeException) as error:
            client.get_open_id_configuration()
        error_message = "Meta endpoint! Unexpected status code: 204, with response body: None."
        check_error_message(self, error, error_message)
        connection_mock.get.assert_called_with(path="/.well-known/openid-configuration")

    @patch("weaviate.client.Client.get_meta", return_value={"version": "1.13.2"})
    def test_timeout_config(self, mock_get_meta):
        """
        Test the `set_timeout_config` method.
        """

        client = Client("http://some_url.com", auth_client_secret=None, timeout_config=(1, 2))
        self.assertEqual(client.timeout_config, (1, 2))
        client.timeout_config = (4, 20)  # ;)
        self.assertEqual(client.timeout_config, (4, 20))
