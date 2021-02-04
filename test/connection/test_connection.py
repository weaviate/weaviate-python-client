import unittest
from unittest.mock import patch, Mock
import requests
from requests import RequestException
from weaviate.exceptions import AuthenticationFailedException
from weaviate.connect import Connection
from weaviate.connect import REST_METHOD_GET
from weaviate.connect import REST_METHOD_POST
from weaviate.connect import REST_METHOD_PUT
from weaviate.connect import REST_METHOD_PATCH
from weaviate.connect import REST_METHOD_DELETE
from weaviate.util import _get_valid_timeout_config as valid_cnfg
from test.util import check_error_message


class TestConnection(unittest.TestCase):

    def check_connection_attributes(self,
            connection: Connection,
            url='test_url/v1',
            timeout_config=(2, 20),
            auth_expires=0,
            auth_bearer=0,
            auth_client_secret=None,
            is_authentication_required=False
        ):
        """
        Check the attributes of the connection value. Assign 'skip' to
        an attribute to skip testing. The attributes have the dafault constructor values.
        """

        if url != 'skip':
            self.assertEqual(connection.url, url)
        if timeout_config != 'skip':
            self.assertEqual(connection.timeout_config, timeout_config)
        if auth_expires != 'skip':
            self.assertEqual(connection.auth_expires, auth_expires)
        if auth_bearer != 'skip':
            self.assertEqual(connection.auth_bearer, auth_bearer)
        if auth_client_secret != 'skip':
            if auth_client_secret is None:
                self.assertIsNone(connection.auth_client_secret)
            else:
                self.assertEqual(connection.auth_client_secret, auth_client_secret)
        if is_authentication_required != 'skip':
            if is_authentication_required is True:
                self.assertTrue(connection.is_authentication_required)
            else:
                self.assertFalse(connection.is_authentication_required)

    @patch("weaviate.connect.connection.Connection._refresh_authentication")
    @patch("weaviate.connect.connection.requests")
    def test__init__(self, mock_requests, mock_refresh_authentication):
        """
        Test the `__init__` method.
        """

        # error messages
        auth_error_message = ("No login credentials provided. The weaviate instance at "
                        "test_url requires login credential, use argument 'auth_client_secret'.")
        # requests error
        mock_requests.get.side_effect = Exception('Test!')
        connection = Connection('test_url')
        self.check_connection_attributes(connection)
        mock_requests.get.assert_called_with(
            "test_url/v1/.well-known/openid-configuration",
            headers={"content-type": "application/json"},
            timeout=(30, 45)
        )
        mock_refresh_authentication.assert_not_called()

        # non 200 status_code return
        mock_requests.get.side_effect = None
        mock_response = Mock(status_code=400)
        mock_requests.get.return_value = mock_response
        connection = Connection('test_url', timeout_config=[3, 23])
        self.check_connection_attributes(connection, timeout_config=(3, 23))
        mock_requests.get.assert_called_with(
            "test_url/v1/.well-known/openid-configuration",
            headers={"content-type": "application/json"},
            timeout=(30, 45)
        )
        mock_refresh_authentication.assert_not_called()

        # 200 status_code return and no auth provided
        mock_requests.get.side_effect = None
        mock_response = Mock(status_code=200)
        mock_requests.get.return_value = mock_response
        with self.assertRaises(ValueError) as error:
            Connection('test_url')
        check_error_message(self, error, auth_error_message)
        mock_requests.get.assert_called_with(
            "test_url/v1/.well-known/openid-configuration",
            headers={"content-type": "application/json"},
            timeout=(30, 45)
        )

        # 200 status_code return and auth provided
        with patch("weaviate.connect.connection.isinstance") as mock_func: # mock is instance method
            mock_func.return_value = True # isinstance returns True for any calls
            mock_requests.get.side_effect = None
            mock_response = Mock(status_code=200)
            mock_requests.get.return_value = mock_response
            connection = Connection('test_url')
            self.check_connection_attributes(connection, is_authentication_required=True)
            mock_requests.get.assert_called_with(
                "test_url/v1/.well-known/openid-configuration",
                headers={"content-type": "application/json"},
                timeout=(30, 45)
            )
            mock_refresh_authentication.assert_called()

    @patch("weaviate.connect.connection.requests")
    def test_run_rest(self, mock_requests):
        """
        Test the `run_rest` method.
        """

        connection = Connection("http://weaviate:1234")

        mock_requests.get.return_value = "GET"
        mock_requests.put.return_value = "PUT"
        mock_requests.post.return_value = "POST"
        mock_requests.patch.return_value = "PATCH"
        mock_requests.delete.return_value = "DELETE"

        # GET method
        self.assertEqual(
            connection.run_rest("path", REST_METHOD_GET, {}, None),
            "GET"
        )
        # PUT method
        self.assertEqual(
            connection.run_rest("path", REST_METHOD_PUT, {}, {}),
            "PUT"
        )
        # POST method
        self.assertEqual(
            connection.run_rest("path", REST_METHOD_POST, {}, {}),
            "POST"
        )
        # PATCH method
        self.assertEqual(
            connection.run_rest("path", REST_METHOD_PATCH, {}, {}),
            "PATCH"
        )
        # DELETE method
        self.assertEqual(
            connection.run_rest("path", REST_METHOD_DELETE, {}, {}),
            "DELETE"
        )
        
        self.assertIsNone(connection.run_rest("path", 12, {}, {}))

    @patch("weaviate.connect.connection.Connection._refresh_authentication")
    def test__get_request_header(self, mock_refresh_authentication):
        """
        Test the `_get_request_header` method.
        """

        connection = Connection('test_url')

        # with no auth
        connection.is_authentication_required = False
        result = connection._get_request_header()
        self.assertEqual(result, {"content-type": "application/json"})
        mock_refresh_authentication.assert_not_called()

        # with auth
        connection.is_authentication_required = True
        connection.auth_bearer = 'test'
        result = connection._get_request_header()
        self.assertEqual(result, {"content-type": "application/json", "Authorization": "Bearer test"})
        mock_refresh_authentication.assert_called()

    @patch("weaviate.connect.connection.requests")
    @patch("weaviate.connect.connection.get_epoch_time")
    def test__refresh_authentication(self, mock_get_epoch_time, mock_requests):
        """
        Test the `_refresh_authentication` method.
        """

        # test the un-expired connection
        mock_get_epoch_time.return_value = -2

        connection = Connection('test_url', None, None)
        mock_requests.reset_mock() # reset 'requests' mock because it is called in the `__init__`
        self.check_connection_attributes(connection) # befor the `_refresh_authentication` call
        connection._refresh_authentication()
        self.check_connection_attributes(connection) # after the `_refresh_authentication` call
        mock_get_epoch_time.assert_called()
        mock_requests.get.assert_not_called()

        # error messages
        data_error_message = "Cannot connect to weaviate."
        data_status_code_error_message = "Cannot authenticate http status not ok."
        add_info_error_message = ("Can't connect to the third party authentication service. "
            "Check that it is running.")
        add_info_status_code_error_message = "Status not OK in connection to the third party authentication service."
        credentials_error_message = ("The grant_types supported by the thirdparty authentication service are "
            "insufficient. Please add 'client_credentials'.")
        oauth_error_message = ("Unable to get a OAuth token from server. Are the credentials "
            "and URLs correct?")
        oauth_status_code_error_message = "Authtentication access denied. Are the credentials correct?"

        # test the expired connection
        mock_get_epoch_time.return_value = 200

        # helper function
        def helper_before_call(*args, **kwargs):
            """
            initialize mock objects and connection before testing th exception.

            Returns
            -------
            weaviate.connect.Connection
                Connection.
            """

            mock_second_get_call.called = False
            mock_get_epoch_time.reset_mock() # reset mock.called
            # reset 'requests' mock because it is called in the `__init__`
            mock_requests.get.reset_mock(side_effect=True, return_value=True)
            connection = Connection(*args, auth_client_secret=kwargs.get("auth_client_secret", None))
            mock_requests.get.configure_mock(**kwargs['get'])
            if 'post' in kwargs:
                mock_requests.post.reset_mock(side_effect=True, return_value=True)
                mock_requests.post.configure_mock(**kwargs['post'])
            self.check_connection_attributes(
                connection,
                url=kwargs.get("url", 'test_url/v1'),
                timeout_config=kwargs.get("timeout_config", (2, 20)),
                auth_expires=kwargs.get("auth_expires", 0),
                auth_bearer=kwargs.get("auth_bearer", 0),
                auth_client_secret=kwargs.get("auth_client_secret", None),
                is_authentication_required=kwargs.get("is_authentication_required", False),
                )
            return connection
            
        def helper_after_call(message, *args, **kwargs):
            """
            initialize mock objects and connection after testing th exception.

            Returns
            -------
            weaviate.connect.Connection
                Connection.
            """

            if message is not None:
                check_error_message(self, error, message)
            self.check_connection_attributes(
                connection,
                url=kwargs.get("url", 'test_url/v1'),
                timeout_config=kwargs.get("timeout_config", (2, 20)),
                auth_expires=kwargs.get("auth_expires", 0),
                auth_bearer=kwargs.get("auth_bearer", 0),
                auth_client_secret=kwargs.get("auth_client_secret", None),
                is_authentication_required=kwargs.get("is_authentication_required", False),
                )
            mock_get_epoch_time.assert_called()
            if 'get' in kwargs:
                mock_requests.get.assert_called_with(*kwargs['get_args'], **kwargs['get']) # only last call of this method
            if 'post' in kwargs:
                mock_requests.post.assert_called_with(*kwargs['post_args'], **kwargs['post']) # only last call of this method

        def mock_second_get_call(first_call_func, second_call_func, *args, **kwargs):
            """
            Mock different results from requests.get
            NOTE: Use >>mock_second_get_call.called = False before calling/using this function.
                    It is used in the `helper_before_call`.
            """

            if mock_second_get_call.called:
                return second_call_func()
            mock_second_get_call.called = True
            return first_call_func() # first call of request.get

        # requests.get exception (get data)
        connection = helper_before_call('test_url', get={'side_effect' :RequestException('Test!')})
        with self.assertRaises(AuthenticationFailedException) as error:
            connection._refresh_authentication()
        get_kwargs = {
            'headers': {"content-type": "application/json"},
            'timeout': (30, 45)
        }
        helper_after_call(data_error_message, get_args=["test_url/v1/.well-known/openid-configuration"], get=get_kwargs)

        # bad status_code (get data)
        connection = helper_before_call('test_url', get={'status_code': 404})
        with self.assertRaises(AuthenticationFailedException) as error:
            connection._refresh_authentication()
        get_kwargs = {
            'headers': {"content-type": "application/json"},
            'timeout': (30, 45)
        }
        helper_after_call(data_status_code_error_message, get_args=["test_url/v1/.well-known/openid-configuration"], get=get_kwargs)

        # requests.get exception (get additional info)
        response = Mock(status_code=200)
        response.json.return_value = {'clientId': 'Test!ID', 'href': "test_href"}
        first_call_behaviour = lambda: response
        second_call_behaviour = lambda: exec('raise RequestException("Test!")')
        connection = helper_before_call(
            'test_url',
            get={'side_effect': lambda *args, **kwargs: mock_second_get_call(first_call_behaviour, second_call_behaviour)}
        )
        with self.assertRaises(AuthenticationFailedException) as error:
            connection._refresh_authentication()
        get_kwargs = {
            'headers': {"content-type": "application/json"},
            'timeout': (30, 45)
        }
        helper_after_call(add_info_error_message, get_args=["test_href"], get=get_kwargs)

        # bad status_code (get additional info)
        response = Mock(status_code=200)
        response.json.return_value = {'clientId': 'Test!ID', 'href': "test_href"}
        first_call_behaviour = lambda: response
        second_call_behaviour = lambda: Mock(status_code=204)
        connection = helper_before_call(
            'test_url',
            get={'side_effect': lambda *args, **kwargs: mock_second_get_call(first_call_behaviour, second_call_behaviour)}
        )
        with self.assertRaises(AuthenticationFailedException) as error:
            connection._refresh_authentication()
        get_kwargs = {
            'headers': {"content-type": "application/json"},
            'timeout': (30, 45)
        }
        helper_after_call(add_info_status_code_error_message, get_args=["test_href"], get=get_kwargs)

        # client_credentials error 
        response = Mock(status_code=200)
        response.json.return_value = {'clientId': 'Test!ID', 'href': "test_href"}
        first_call_behaviour = lambda: response
        request_third_part = Mock(status_code=200)
        request_third_part.json.return_value = {'grant_types_supported': {'Test_key': 'Test_value'}}
        second_call_behaviour = lambda: request_third_part
        connection = helper_before_call(
            'test_url',
            get={'side_effect': lambda *args, **kwargs: mock_second_get_call(first_call_behaviour, second_call_behaviour)}
        )
        with self.assertRaises(AuthenticationFailedException) as error:
            connection._refresh_authentication()
        get_kwargs = {
            'headers': {"content-type": "application/json"},
            'timeout': (30, 45)
        }
        helper_after_call(credentials_error_message, get_args=["test_href"], get=get_kwargs)

        # OAuth error 
        response = Mock(status_code=200)
        response.json.return_value = {'clientId': 'Test!ID', 'href': "test_href"}
        first_call_behaviour = lambda: response
        request_third_part = Mock(status_code=200)
        request_third_part.json.return_value = {
            'grant_types_supported': {'client_credentials': 'Test_cred!'},
            'token_endpoint': 'Test'}
        second_call_behaviour = lambda: request_third_part
        mock_auth = Mock()
        mock_auth.get_credentials.return_value = {'test_key': 'Value'}
        connection = helper_before_call(
            'test_url',
            auth_client_secret=mock_auth,
            get={'side_effect': lambda *args, **kwargs: mock_second_get_call(first_call_behaviour, second_call_behaviour)},
            post={'side_effect': RequestException('Test')}
            )
        with self.assertRaises(AuthenticationFailedException) as error:
            connection._refresh_authentication()
        get_kwargs = {
            'headers': {"content-type": "application/json"},
            'timeout': (30, 45)
        }
        get_args = ["test_href"]
        post_kwargs = {'timeout': (30, 45)}
        post_args = ["Test", {'client_id': 'Test!ID', 'test_key': 'Value'}]
        helper_after_call(
            oauth_error_message,
            get=get_kwargs,
            get_args=get_args,
            post=post_kwargs,
            post_args=post_args,
            auth_client_secret=mock_auth
        )

        # OAuth status_code error 
        response = Mock(status_code=200)
        response.json.return_value = {'clientId': 'Test!ID', 'href': "test_href"}
        first_call_behaviour = lambda: response
        request_third_part = Mock(status_code=200)
        request_third_part.json.return_value = {
            'grant_types_supported': {'client_credentials': 'Test_cred!'},
            'token_endpoint': 'Test'}
        second_call_behaviour = lambda: request_third_part
        mock_auth = Mock()
        mock_auth.get_credentials.return_value = {'test_key': 'Value'}
        connection = helper_before_call(
            'test_url',
            auth_client_secret=mock_auth,
            get={'side_effect': lambda *args, **kwargs: mock_second_get_call(first_call_behaviour, second_call_behaviour)},
            post={'return_value': Mock(status_code=401)}
            )
        with self.assertRaises(AuthenticationFailedException) as error:
            connection._refresh_authentication()
        get_kwargs = {
            'headers': {"content-type": "application/json"},
            'timeout': (30, 45)
        }
        get_args = ["test_href"]
        post_kwargs = {'timeout': (30, 45)}
        post_args = ["Test", {'client_id': 'Test!ID', 'test_key': 'Value'}]
        helper_after_call(
            oauth_status_code_error_message,
            get=get_kwargs,
            get_args=get_args,
            post=post_kwargs,
            post_args=post_args,
            auth_client_secret=mock_auth
        )

        # valid call
        response = Mock(status_code=200)
        response.json.return_value = {'clientId': 'Test!ID', 'href': "test_href"}
        first_call_behaviour = lambda: response
        request_third_part = Mock(status_code=200)
        request_third_part.json.return_value = {
            'grant_types_supported': {'client_credentials': 'Test_cred!'},
            'token_endpoint': 'Test'}
        second_call_behaviour = lambda: request_third_part
        mock_auth = Mock()
        mock_auth.get_credentials.return_value = {'test_key': 'Value'}
        mock_post_response = Mock(status_code=400)
        mock_post_response.json.return_value = {
            'access_token': 'TestBearer!',
            'expires_in': 1234
        }
        connection = helper_before_call(
            'test_url',
            auth_client_secret=mock_auth,
            get={'side_effect': lambda *args, **kwargs: mock_second_get_call(first_call_behaviour, second_call_behaviour)},
            post={'return_value': mock_post_response}
            )
        connection._refresh_authentication()
        get_kwargs = {
            'headers': {"content-type": "application/json"},
            'timeout': (30, 45)
        }
        get_args = ["test_href"]
        post_kwargs = {'timeout': (30, 45)}
        post_args = ["Test", {'client_id': 'Test!ID', 'test_key': 'Value'}]
        helper_after_call(
            None,
            get=get_kwargs,
            get_args=get_args,
            post=post_kwargs,
            post_args=post_args,
            auth_client_secret=mock_auth,
            auth_expires='skip',#1234 + 200 - 2,
            auth_bearer='TestBearer!'
        )



    def test_timeout_config(self):
        """
        Test the setter and getter of `timeout_config`.
        """

        connection = Connection('test_url')

        # default one
        self.assertEqual(connection.timeout_config, (2, 20))

        with patch('weaviate.connect.connection._get_valid_timeout_config', side_effect=valid_cnfg) as mock_obj: # to test if called
            connection.timeout_config = (4, 210)
            self.assertEqual(connection.timeout_config, (4, 210))
            mock_obj.assert_called_with((4, 210))

    @patch("weaviate.connect.connection.datetime")
    def test_get_epoch_time(self, mock_datetime):
        """
        Test the `get_epoch_time` function.
        """

        import datetime
        import time
        from weaviate.connect.connection import get_epoch_time

        from time import mktime

        zero_epoch = datetime.datetime.fromtimestamp(0)
        mock_datetime.datetime.utcnow.return_value = zero_epoch
        self.assertEqual(get_epoch_time(), 0)

        epoch = datetime.datetime.fromtimestamp(110.56)
        mock_datetime.datetime.utcnow.return_value = epoch
        self.assertEqual(get_epoch_time(), 111)

        epoch = datetime.datetime.fromtimestamp(110.46)
        mock_datetime.datetime.utcnow.return_value = epoch
        self.assertEqual(get_epoch_time(), 110)
