import unittest
from unittest.mock import patch

from test.util import check_error_message
from weaviate.connect.base import _get_proxies
from weaviate.connect.v3 import Connection
from weaviate.util import _get_valid_timeout_config


class TestConnection(unittest.TestCase):
    def check_connection_attributes(
        self,
        connection: Connection,
        url="test_url",
        timeout_config=(2, 20),
        oidc_auth_flow=False,
        headers=None,
    ):
        """
        Check the attributes of the connection value. Assign 'skip' to
        an attribute to skip testing. The attributes have the default constructor values.
        """

        if headers is None:
            headers = {"content-type": "application/json"}
        if url != "skip":
            self.assertEqual(connection.url, url)
        if timeout_config != "skip":
            self.assertEqual(connection.timeout_config, timeout_config)
        if oidc_auth_flow != "skip":
            if oidc_auth_flow is True:
                self.assertIsNotNone(connection._auth)
            else:
                self.assertIsNone(connection._auth)
        if headers != "skip":
            self.assertEqual(connection._headers, headers)

    @patch("weaviate.connect.base.datetime")
    def test_get_epoch_time(self, mock_datetime):
        """
        Test the `get_epoch_time` function.
        """

        import datetime
        from weaviate.connect.base import _get_epoch_time

        zero_epoch = datetime.datetime.fromtimestamp(0)
        mock_datetime.datetime.utcnow.return_value = zero_epoch
        self.assertEqual(_get_epoch_time(), 0)

        epoch = datetime.datetime.fromtimestamp(110.56)
        mock_datetime.datetime.utcnow.return_value = epoch
        self.assertEqual(_get_epoch_time(), 111)

        epoch = datetime.datetime.fromtimestamp(110.46)
        mock_datetime.datetime.utcnow.return_value = epoch
        self.assertEqual(_get_epoch_time(), 110)

    @patch("weaviate.connect.base.os")
    def test_get_proxies(self, os_mock):
        """
        Test the `_get_proxies` function.
        """

        error_msg = lambda dt: (
            "If 'proxies' is not None, it must be of type dict, str, or wvc.init.Proxies. "
            f"Given type: {dt}."
        )
        with self.assertRaises(TypeError) as error:
            proxies = _get_proxies([], False)
        check_error_message(self, error, error_msg(list))

        proxies = _get_proxies({}, False)
        self.assertEqual(proxies, {})

        proxies = _get_proxies({"test": True}, False)
        self.assertEqual(proxies, {"test": True})

        proxies = _get_proxies({"test": True}, True)
        self.assertEqual(proxies, {"test": True})

        proxies = _get_proxies("test", True)
        self.assertEqual(proxies, {"http": "test", "https": "test", "grpc": "test"})

        os_mock.environ.get.return_value = None
        proxies = _get_proxies(None, True)
        self.assertEqual(proxies, {})

        os_mock.environ.get.return_value = "test"
        proxies = _get_proxies(None, True)
        self.assertEqual(proxies, {"http": "test", "https": "test", "grpc": "test"})

    def test__get_valid_timeout_config(self):
        """
        Test the `_get_valid_timeout_config` function.
        """

        # incalid calls
        negative_num_error_message = "'timeout_config' cannot be non-positive number/s!"
        type_error_message = "'timeout_config' should be a (or tuple of) positive number/s!"
        value_error_message = "'timeout_config' must be of length 2!"
        value_types_error_message = "'timeout_config' must be tuple of numbers"

        ## wrong type
        with self.assertRaises(TypeError) as error:
            _get_valid_timeout_config(None)
        check_error_message(self, error, type_error_message)

        with self.assertRaises(TypeError) as error:
            _get_valid_timeout_config(True)
        check_error_message(self, error, type_error_message)

        with self.assertRaises(TypeError) as error:
            _get_valid_timeout_config("(2, 13)")
        check_error_message(self, error, type_error_message)

        ## wrong tuple length 3
        with self.assertRaises(ValueError) as error:
            _get_valid_timeout_config((1, 2, 3))
        check_error_message(self, error, value_error_message)

        ## wrong value types
        with self.assertRaises(TypeError) as error:
            _get_valid_timeout_config((None, None))
        check_error_message(self, error, value_types_error_message)

        with self.assertRaises(TypeError) as error:
            _get_valid_timeout_config(("1", 10))
        check_error_message(self, error, value_types_error_message)

        with self.assertRaises(TypeError) as error:
            _get_valid_timeout_config(("1", "10"))
        check_error_message(self, error, value_types_error_message)

        with self.assertRaises(TypeError) as error:
            _get_valid_timeout_config((True, False))
        check_error_message(self, error, value_types_error_message)

        ## non-positive numbers
        with self.assertRaises(ValueError) as error:
            _get_valid_timeout_config(0)
        check_error_message(self, error, negative_num_error_message)

        with self.assertRaises(ValueError) as error:
            _get_valid_timeout_config(-1)
        check_error_message(self, error, negative_num_error_message)

        with self.assertRaises(ValueError) as error:
            _get_valid_timeout_config(-4.134)
        check_error_message(self, error, negative_num_error_message)

        with self.assertRaises(ValueError) as error:
            _get_valid_timeout_config((-3.5, 1.5))
        check_error_message(self, error, negative_num_error_message)

        with self.assertRaises(ValueError) as error:
            _get_valid_timeout_config((3, -1.5))
        check_error_message(self, error, negative_num_error_message)

        with self.assertRaises(ValueError) as error:
            _get_valid_timeout_config((0, 0))
        check_error_message(self, error, negative_num_error_message)

        # valid calls
        self.assertEqual(_get_valid_timeout_config((2, 20)), (2, 20))
        self.assertEqual(_get_valid_timeout_config((3.5, 2.34)), (3.5, 2.34))
        self.assertEqual(_get_valid_timeout_config(4.32), (4.32, 4.32))
