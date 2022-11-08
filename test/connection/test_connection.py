from operator import add
import unittest
from unittest.mock import patch, Mock
from requests import RequestException
from weaviate.auth import AuthClientPassword
from weaviate.exceptions import AuthenticationFailedException
from weaviate.connect.connection import Connection, _get_proxies, _get_valid_timeout_config
from test.util import check_error_message


class TestConnection(unittest.TestCase):
    def check_connection_attributes(
        self,
        connection: Connection,
        url="test_url",
        timeout_config=(2, 20),
        auth_expires=0,
        auth_bearer=None,
        auth_client_secret=None,
        oidc_auth_flow=False,
        headers={"content-type": "application/json"},
    ):
        """
        Check the attributes of the connection value. Assign 'skip' to
        an attribute to skip testing. The attributes have the default constructor values.
        """

        if url != "skip":
            self.assertEqual(connection.url, url)
        if timeout_config != "skip":
            self.assertEqual(connection.timeout_config, timeout_config)
        if auth_expires != "skip":
            self.assertEqual(connection._auth_expires, auth_expires)
        if auth_bearer != "skip":
            self.assertEqual(connection._auth_bearer, auth_bearer)
        if auth_client_secret != "skip":
            if auth_client_secret is not None:
                self.assertEqual(connection._auth_client_secret, auth_client_secret)
        if oidc_auth_flow != "skip":
            if oidc_auth_flow is True:
                self.assertTrue(connection._oidc_auth_flow)
            else:
                self.assertFalse(connection._oidc_auth_flow)
        if headers != "skip":
            self.assertEqual(connection._headers, headers)

    @patch("weaviate.connect.connection.Connection._refresh_authentication")
    @patch("weaviate.connect.connection.requests")
    def test__init__(self, mock_requests, mock_refresh_authentication):
        """
        Test the `__init__` method.
        """

        # error messages
        auth_error_message = (
            "No login credentials provided. The weaviate instance at "
            "test_url requires login credential, use argument 'auth_client_secret'."
        )
        ad_headers_err_message = lambda dt: (
            "'additional_headers' must be of type dict or None. " f"Given type: {dt}."
        )

        # requests error
        mock_session = mock_requests.Session.return_value = Mock()

        # additional_headers error check

        with self.assertRaises(TypeError) as error:
            Connection(
                url="test_url",
                auth_client_secret=None,
                timeout_config=(3, 23),
                proxies=None,
                trust_env=False,
                additional_headers=["test", True],
            )
        check_error_message(self, error, ad_headers_err_message(list))
        mock_session.get.assert_not_called()

        # non 200 status_code return
        mock_session.get.side_effect = None
        mock_response = Mock(status_code=400)
        mock_session.get.return_value = mock_response
        connection = Connection(
            url="test_url",
            auth_client_secret=None,
            timeout_config=(3, 23),
            proxies=None,
            trust_env=False,
            additional_headers=None,
        )
        self.check_connection_attributes(connection, timeout_config=(3, 23))
        mock_session.get.assert_called_with(
            "test_url/v1/.well-known/openid-configuration",
            headers={"content-type": "application/json"},
            proxies={},
            timeout=(3, 23),
        )
        mock_refresh_authentication.assert_not_called()

        # 200 status_code return and no auth provided
        mock_session.get.side_effect = None
        mock_response = Mock(status_code=200)
        mock_session.get.return_value = mock_response
        with self.assertRaises(ValueError) as error:
            Connection(
                url="test_url",
                auth_client_secret=None,
                timeout_config=(2, 20),
                proxies={},
                trust_env=False,
                additional_headers=None,
            )
        check_error_message(self, error, auth_error_message)
        mock_session.get.assert_called_with(
            "test_url/v1/.well-known/openid-configuration",
            headers={"content-type": "application/json"},
            timeout=(2, 20),
            proxies={},
        )

        # 200 status_code return and auth provided
        with patch(
            "weaviate.connect.connection.isinstance"
        ) as mock_func:  # mock is instance method
            with patch("weaviate.connect.connection._get_valid_timeout_config") as mock_get_timeout:
                mock_get_timeout.return_value = (2, 20)
                mock_func.return_value = True  # isinstance returns True for any calls
                mock_session.get.side_effect = None
                mock_response = Mock(status_code=200)
                mock_session.get.return_value = mock_response
                connection = Connection(
                    url="test_url",
                    auth_client_secret=None,
                    timeout_config=(2, 20),
                    proxies=None,
                    trust_env=False,
                    additional_headers={"Test": True},
                )
                self.check_connection_attributes(
                    connection,
                    oidc_auth_flow=True,
                    headers={"content-type": "application/json", "test": True},
                )
                mock_session.get.assert_called_with(
                    "test_url/v1/.well-known/openid-configuration",
                    headers={
                        "content-type": "application/json"
                    },  # this has different inplace headers
                    timeout=(2, 20),
                    proxies={},
                )
                mock_refresh_authentication.assert_called()

        # 200 status_code return and token provided
        with patch("weaviate.connect.connection.Connection._log_in") as mock_login:
            connection = Connection(
                url="test_url",
                auth_client_secret=None,
                timeout_config=(2, 20),
                proxies=None,
                trust_env=False,
                additional_headers={"AuthorizatioN": "my token"},
            )
            self.check_connection_attributes(
                connection,
                oidc_auth_flow=False,
                headers={"content-type": "application/json", "authorization": "my token"},
            )
            mock_login.assert_not_called()

    @patch("weaviate.connect.connection.requests")
    def test_all_requests_methods(self, mock_requests):
        """
        Test the all requests methods ('get', 'put', 'patch', 'post', 'delete').
        """

        mock_session = mock_requests.Session.return_value = Mock()
        connection = Connection(
            url="http://weaviate:1234",
            auth_client_secret=None,
            timeout_config=(2, 20),
            proxies=None,
            trust_env=False,
            additional_headers=None,
        )

        # GET method with param
        connection.get("/get", {"test": None}),
        mock_session.get.assert_called_with(
            url="http://weaviate:1234/v1/get",
            headers={"content-type": "application/json"},
            timeout=(2, 20),
            proxies={},
            params={"test": None},
        )
        mock_session.reset_mock()

        # GET method without param
        connection.get("/get"),
        mock_session.get.assert_called_with(
            url="http://weaviate:1234/v1/get",
            headers={"content-type": "application/json"},
            timeout=(2, 20),
            proxies={},
            params={},
        )
        mock_session.reset_mock()

        # PUT method
        connection.put("/put", {"PUT": "test"}),
        mock_session.put.assert_called_with(
            url="http://weaviate:1234/v1/put",
            json={"PUT": "test"},
            headers={"content-type": "application/json"},
            timeout=(2, 20),
            proxies={},
        )
        mock_session.reset_mock()

        # POST method
        connection.post("/post", {"POST": "TeST!"}),
        mock_session.post.assert_called_with(
            url="http://weaviate:1234/v1/post",
            json={"POST": "TeST!"},
            headers={"content-type": "application/json"},
            timeout=(2, 20),
            proxies={},
        )
        mock_session.reset_mock()

        # PATCH method
        connection.patch("/patch", {"PATCH": "teST"}),
        mock_session.patch.assert_called_with(
            url="http://weaviate:1234/v1/patch",
            json={"PATCH": "teST"},
            headers={"content-type": "application/json"},
            timeout=(2, 20),
            proxies={},
        )
        mock_session.reset_mock()

        # DELETE method
        connection.delete("/delete", {"DELETE": "TESt"}),
        mock_session.delete.assert_called_with(
            url="http://weaviate:1234/v1/delete",
            json={"DELETE": "TESt"},
            headers={"content-type": "application/json"},
            timeout=(2, 20),
            proxies={},
        )

        # add Proxies

        mock_session = mock_requests.Session.return_value = Mock()
        connection = Connection(
            url="http://weaviate:1234",
            auth_client_secret=None,
            timeout_config=(2, 20),
            proxies={"test": True},
            trust_env=False,
            additional_headers=None,
        )

        # GET method with param
        connection.get("/get", {"test": None}),
        mock_session.get.assert_called_with(
            url="http://weaviate:1234/v1/get",
            headers={"content-type": "application/json"},
            timeout=(2, 20),
            proxies={"test": True},
            params={"test": None},
        )
        mock_session.reset_mock()

        # GET method without param
        connection.get("/get"),
        mock_session.get.assert_called_with(
            url="http://weaviate:1234/v1/get",
            headers={"content-type": "application/json"},
            timeout=(2, 20),
            proxies={"test": True},
            params={},
        )
        mock_session.reset_mock()

        # PUT method
        connection.put("/put", {"PUT": "test"}),
        mock_session.put.assert_called_with(
            url="http://weaviate:1234/v1/put",
            json={"PUT": "test"},
            headers={"content-type": "application/json"},
            timeout=(2, 20),
            proxies={"test": True},
        )
        mock_session.reset_mock()

        # POST method
        connection.post("/post", {"POST": "TeST!"}),
        mock_session.post.assert_called_with(
            url="http://weaviate:1234/v1/post",
            json={"POST": "TeST!"},
            headers={"content-type": "application/json"},
            timeout=(2, 20),
            proxies={"test": True},
        )
        mock_session.reset_mock()

        # PATCH method
        connection.patch("/patch", {"PATCH": "teST"}),
        mock_session.patch.assert_called_with(
            url="http://weaviate:1234/v1/patch",
            json={"PATCH": "teST"},
            headers={"content-type": "application/json"},
            timeout=(2, 20),
            proxies={"test": True},
        )
        mock_session.reset_mock()

        # DELETE method
        connection.delete("/delete", {"DELETE": "TESt"}),
        mock_session.delete.assert_called_with(
            url="http://weaviate:1234/v1/delete",
            json={"DELETE": "TESt"},
            headers={"content-type": "application/json"},
            timeout=(2, 20),
            proxies={"test": True},
        )

    @patch("weaviate.connect.connection.Connection._log_in", Mock())
    @patch("weaviate.connect.connection.Connection._refresh_authentication")
    def test__get_request_header(self, mock_refresh_authentication):
        """
        Test the `_get_request_header` method.
        """

        connection = Connection(
            url="http://test_url",
            auth_client_secret=None,
            timeout_config=(3, 23),
            proxies=None,
            trust_env=False,
            additional_headers=None,
        )

        # with no auth
        connection._oidc_auth_flow = False
        result = connection._get_request_header()
        self.assertEqual(result, {"content-type": "application/json"})
        mock_refresh_authentication.assert_not_called()

        # with auth
        connection._oidc_auth_flow = True
        connection._auth_bearer = "test"
        result = connection._get_request_header()
        self.assertEqual(
            result, {"content-type": "application/json", "Authorization": "Bearer test"}
        )
        mock_refresh_authentication.assert_called()

        # with additional headers
        connection = Connection(
            url="http://test_url",
            auth_client_secret=None,
            timeout_config=(3, 23),
            proxies=None,
            trust_env=False,
            additional_headers={"Test": "This is a test", "test2": True},
        )

        mock_refresh_authentication.reset_mock()
        connection._oidc_auth_flow = False
        result = connection._get_request_header()
        self.assertEqual(
            result, {"content-type": "application/json", "test": "This is a test", "test2": True}
        )
        mock_refresh_authentication.assert_not_called()

    @patch("weaviate.connect.connection.Connection._log_in", Mock())
    @patch("weaviate.connect.connection.requests")
    @patch("weaviate.connect.connection._get_epoch_time")
    @patch("weaviate.connect.connection.Connection._set_bearer")
    def test__refresh_authentication(self, mock_set_bearer, mock_get_epoch_time, mock_requests):
        """
        Test the `_refresh_authentication` method.
        """

        # test the un-expired connection
        mock_get_epoch_time.return_value = -2

        mock_session = mock_requests.Session.return_value = Mock()
        connection = Connection(
            url="test_url",
            auth_client_secret=None,
            timeout_config=(2, 20),
            proxies=None,
            trust_env=False,
            additional_headers=None,
        )
        mock_session.reset_mock()  # reset 'requests' mock because it is called in the `__init__`
        self.check_connection_attributes(  # before the `_refresh_authentication` call
            connection,
            timeout_config=(2, 20),
        )
        connection._refresh_authentication()
        self.check_connection_attributes(
            connection,
            timeout_config=(2, 20),
        )
        mock_get_epoch_time.assert_called()
        mock_session.get.assert_not_called()
        mock_set_bearer.assert_not_called()

        # error messages
        data_error_message = "Cannot connect to weaviate."
        data_status_code_error_message = "Cannot authenticate http status not ok."

        mock_get_epoch_time.return_value = 200
        get_kwargs = {
            "headers": {"content-type": "application/json"},
            "timeout": (30, 45),
            "proxies": {},
        }
        # test the expired connection
        ## requests.get exception (get data)
        connection = Connection(
            url="test_url",
            auth_client_secret=None,
            timeout_config=(2, 20),
            proxies=None,
            trust_env=False,
            additional_headers=None,
        )
        mock_session.get.configure_mock(side_effect=RequestException("Test!"))
        with self.assertRaises(AuthenticationFailedException) as error:
            connection._refresh_authentication()

        check_error_message(self, error, data_error_message)
        mock_session.get.assert_called_with(
            "test_url/v1/.well-known/openid-configuration", **get_kwargs
        )
        mock_set_bearer.assert_not_called()

        ## bad status_code (get data)
        mock_get_epoch_time.reset_mock()  # reset mock.called
        ### reset 'requests' mock because it is called in the `__init__`
        mock_session.get.reset_mock(side_effect=True, return_value=True)
        connection = Connection(
            url="test_url",
            auth_client_secret=None,
            timeout_config=(2, 20),
            proxies=None,
            trust_env=False,
            additional_headers=None,
        )
        mock_session.get.return_value = Mock(status_code=404)
        with self.assertRaises(AuthenticationFailedException) as error:
            connection._refresh_authentication()
        check_error_message(self, error, data_status_code_error_message)
        mock_session.get.assert_called_with(
            "test_url/v1/.well-known/openid-configuration", **get_kwargs
        )
        mock_set_bearer.assert_not_called()

        # valid call
        mock_get_epoch_time.reset_mock()  # reset mock.called
        ## reset 'requests' mock because it is called in the `__init__`
        mock_session.get.reset_mock(side_effect=True, return_value=True)
        connection = Connection(
            url="test_url",
            auth_client_secret=None,
            timeout_config=(3, 23),
            proxies=None,
            trust_env=False,
            additional_headers=None,
        )
        mock_session.get.return_value = Mock(
            **{"status_code": 200, "json.return_value": {"clientId": "Test1!", "href": "Test2!"}}
        )
        connection._refresh_authentication()
        mock_session.get.assert_called_with(
            "test_url/v1/.well-known/openid-configuration", **get_kwargs
        )
        mock_set_bearer.assert_called_with(client_id="Test1!", href="Test2!")

    @patch("weaviate.connect.connection.Connection._log_in", Mock())
    @patch("weaviate.connect.connection.requests")
    @patch("weaviate.connect.connection.Connection._refresh_authentication")
    def test__set_bearer(self, mock_refresh_authentication, mock_requests):
        """
        Test the `_set_bearer` method.
        """

        get_kwargs = {
            "headers": {"content-type": "application/json"},
            "timeout": (30, 45),
            "proxies": {},
        }
        mock_refresh_authentication.return_value = None

        # error messages
        add_info_error_message = (
            "Can't connect to the third party authentication service. " "Check that it is running."
        )
        add_info_status_code_error_message = (
            "Status not OK in connection to the third party authentication service."
        )
        credentials_error_message = lambda gt: (
            "The grant_types supported by the third-party authentication service are "
            f"insufficient. Please add the '{gt}' grant type."
        )
        oauth_error_message = (
            "Unable to get a OAuth token from server. Are the credentials " "and URLs correct?"
        )
        oauth_status_code_error_message = (
            "Authentication access denied. Are the credentials correct?"
        )

        # helper function
        def helper_before_call(**kwargs):
            """
            initialize mock objects and connection before testing th exception.

            Returns
            -------
            weaviate.connect.Connection
                Connection.
            """

            # reset 'requests' mock because it is called in the `__init__`
            mock_requests.get.reset_mock(side_effect=True, return_value=True)
            mock_requests.post.reset_mock(side_effect=True, return_value=True)
            connection = Connection(
                url=kwargs["url"],
                auth_client_secret=kwargs.get("auth_client_secret"),
                timeout_config=(2, 20),
                proxies=None,
                trust_env=False,
                additional_headers=None,
            )
            mock_requests.configure_mock(**kwargs["requests"])
            self.check_connection_attributes(
                connection,
                url=kwargs.get("url", "test_url"),
                timeout_config=kwargs.get("timeout_config", (2, 20)),
                auth_expires=kwargs.get("auth_expires", 0),
                auth_bearer=kwargs.get("auth_bearer", None),
                auth_client_secret=kwargs.get("auth_client_secret", None),
                oidc_auth_flow=kwargs.get("oidc_auth_flow", False),
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
                url=kwargs.get("url", "test_url"),
                timeout_config=kwargs.get("timeout_config", (2, 20)),
                auth_expires=kwargs.get("auth_expires", 0),
                auth_bearer=kwargs.get("auth_bearer", None),
                auth_client_secret=kwargs.get("auth_client_secret", None),
                oidc_auth_flow=kwargs.get("oidc_auth_flow", False),
            )
            if "get" in kwargs:
                mock_requests.get.assert_called_with(
                    *kwargs["get_args"], **kwargs["get"]
                )  # only last call of this method
            if "post" in kwargs:
                mock_requests.post.assert_called_with(
                    *kwargs["post_args"], **kwargs["post"]
                )  # only last call of this method

        # requests.get exception (get additional info)
        connection = helper_before_call(
            url="test_url", requests={"get.side_effect": RequestException("Test!")}
        )
        with self.assertRaises(AuthenticationFailedException) as error:
            connection._set_bearer("test_id", "test_href")
        helper_after_call(add_info_error_message, get_args=["test_href"], get=get_kwargs)

        # bad status_code (get additional info)
        connection = helper_before_call(
            url="test_url", requests={"get.return_value": Mock(status_code=204)}
        )
        with self.assertRaises(AuthenticationFailedException) as error:
            connection._set_bearer("test_id", "test_href")
        helper_after_call(
            add_info_status_code_error_message, get_args=["test_href"], get=get_kwargs
        )

        # client_credentials error
        request_third_part = Mock(status_code=200)
        request_third_part.json.return_value = {"grant_types_supported": ["Test"]}
        connection = helper_before_call(
            url="test_url",
            requests={"get.return_value": request_third_part},
            auth_client_secret=AuthClientPassword("u", "p"),
        )
        with self.assertRaises(AuthenticationFailedException) as error:
            connection._set_bearer("test_id", "test_href")
        get_kwargs = {
            "headers": {"content-type": "application/json"},
            "timeout": (30, 45),
            "proxies": {},
        }
        helper_after_call(
            credentials_error_message("password"), get_args=["test_href"], get=get_kwargs
        )

        # OAuth error
        request_third_part = Mock(status_code=200)
        request_third_part.json.return_value = {
            "grant_types_supported": ["client_credentials", "test"],
            "token_endpoint": "Test",
        }
        mock_auth = Mock(**{"get_credentials.return_value": {"grant_type": "test"}})
        connection = helper_before_call(
            url="test_url",
            auth_client_secret=mock_auth,
            requests={
                "get.return_value": request_third_part,
                "post.side_effect": RequestException("Test"),
            },
        )
        with self.assertRaises(AuthenticationFailedException) as error:
            connection._set_bearer("test_id", "test_href")
        get_kwargs = {
            "headers": {"content-type": "application/json"},
            "timeout": (30, 45),
            "proxies": {},
        }
        get_args = ["test_href"]
        post_kwargs = {
            "timeout": (30, 45),
            "proxies": {},
        }
        post_args = ["Test", {"client_id": "test_id", "grant_type": "test"}]
        helper_after_call(
            oauth_error_message,
            get=get_kwargs,
            get_args=get_args,
            post=post_kwargs,
            post_args=post_args,
            auth_client_secret=mock_auth,
        )

        # OAuth status_code error
        request_third_part = Mock(status_code=200)
        request_third_part.json.return_value = {
            "grant_types_supported": ["client_credentials", "test"],
            "token_endpoint": "Test",
        }
        mock_auth = Mock(**{"get_credentials.return_value": {"grant_type": "test"}})
        connection = helper_before_call(
            url="test_url",
            auth_client_secret=mock_auth,
            requests={
                "get.return_value": request_third_part,
                "post.return_value": Mock(status_code=401),
            },
        )
        with self.assertRaises(AuthenticationFailedException) as error:
            connection._set_bearer("Test!ID", "test_href")
        get_kwargs = {
            "headers": {"content-type": "application/json"},
            "timeout": (30, 45),
            "proxies": {},
        }
        get_args = ["test_href"]
        post_kwargs = {
            "timeout": (30, 45),
            "proxies": {},
        }
        post_args = ["Test", {"client_id": "Test!ID", "grant_type": "test"}]
        helper_after_call(
            oauth_status_code_error_message,
            get=get_kwargs,
            get_args=get_args,
            post=post_kwargs,
            post_args=post_args,
            auth_client_secret=mock_auth,
        )

        # valid call
        request_third_part = Mock(status_code=200)
        request_third_part.json.return_value = {
            "grant_types_supported": ["test"],
            "token_endpoint": "Test",
        }
        mock_auth = Mock(**{"get_credentials.return_value": {"grant_type": "test"}})
        mock_post_response = Mock(status_code=400)
        mock_post_response.json.return_value = {"access_token": "TestBearer!", "expires_in": 1234}
        connection = helper_before_call(
            url="test_url",
            auth_client_secret=mock_auth,
            requests={
                "get.return_value": request_third_part,
                "post.return_value": mock_post_response,
            },
        )
        connection._set_bearer("Test!ID", "test_href")
        get_kwargs = {
            "headers": {"content-type": "application/json"},
            "timeout": (30, 45),
            "proxies": {},
        }
        get_args = ["test_href"]
        post_kwargs = {
            "timeout": (30, 45),
            "proxies": {},
        }
        post_args = ["Test", {"client_id": "Test!ID", "grant_type": "test"}]
        helper_after_call(
            None,
            get=get_kwargs,
            get_args=get_args,
            post=post_kwargs,
            post_args=post_args,
            auth_client_secret=mock_auth,
            auth_expires="skip",  # 1234 + 200 - 2,
            auth_bearer="TestBearer!",
        )

    @patch("weaviate.connect.connection.Connection._log_in")
    def test_timeout_config(self, mock_log_in):
        """
        Test the setter and getter of `timeout_config`.
        """

        connection = Connection(
            url="http://test_url",
            auth_client_secret=None,
            timeout_config=(2, 20),
            proxies=None,
            trust_env=False,
            additional_headers=None,
        )
        mock_log_in.assert_called()

        # default one
        self.assertEqual(connection.timeout_config, (2, 20))

        connection.timeout_config = (4, 210)
        self.assertEqual(connection.timeout_config, (4, 210))

    @patch("weaviate.connect.connection.datetime")
    def test_get_epoch_time(self, mock_datetime):
        """
        Test the `get_epoch_time` function.
        """

        import datetime
        from weaviate.connect.connection import _get_epoch_time

        zero_epoch = datetime.datetime.fromtimestamp(0)
        mock_datetime.datetime.utcnow.return_value = zero_epoch
        self.assertEqual(_get_epoch_time(), 0)

        epoch = datetime.datetime.fromtimestamp(110.56)
        mock_datetime.datetime.utcnow.return_value = epoch
        self.assertEqual(_get_epoch_time(), 111)

        epoch = datetime.datetime.fromtimestamp(110.46)
        mock_datetime.datetime.utcnow.return_value = epoch
        self.assertEqual(_get_epoch_time(), 110)

    @patch("weaviate.connect.connection.os")
    def test_get_proxies(self, os_mock):
        """
        Test the `_get_proxies` function.
        """

        error_msg = lambda dt: (
            "If 'proxies' is not None, it must be of type dict or str. " f"Given type: {dt}."
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
        self.assertEqual(proxies, {"http": "test", "https": "test"})

        os_mock.environ.get.return_value = None
        proxies = _get_proxies(None, True)
        self.assertEqual(proxies, {})

        os_mock.environ.get.return_value = "test"
        proxies = _get_proxies(None, True)
        self.assertEqual(proxies, {"http": "test", "https": "test"})

    def test__get_valid_timeout_config(self):
        """
        Test the `_get_valid_timeout_config` function.
        """

        # incalid calls
        negative_num_error_message = "'timeout_config' cannot be non-positive number/s!"
        type_error_message = "'timeout_config' should be a (or tuple of) positive real number/s!"
        value_error_message = "'timeout_config' must be of length 2!"
        value_types_error_message = "'timeout_config' must be tuple of real numbers"

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
