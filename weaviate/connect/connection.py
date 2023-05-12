"""
Connection class definition.
"""
from __future__ import annotations

import datetime
import os
import socket
import time
from threading import Thread, Event
from typing import Any, Dict, Tuple, Optional, Union
from urllib.parse import urlparse

import requests
from authlib.integrations.requests_client import OAuth2Session
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError as RequestsConnectionError, ReadTimeout
from requests.exceptions import HTTPError as RequestsHTTPError
from requests.exceptions import JSONDecodeError

from weaviate.auth import AuthCredentials, AuthClientCredentials, AuthApiKey
from weaviate.config import ConnectionConfig
from weaviate.connect.authentication import _Auth
from weaviate.embedded import EmbeddedDB
from weaviate.exceptions import (
    AuthenticationFailedException,
    UnexpectedStatusCodeException,
    WeaviateStartUpError,
)
from weaviate.types import NUMBERS
from weaviate.util import _check_positive_num, is_weaviate_domain
from weaviate.warnings import _Warnings

try:
    import grpc
    from weaviate_grpc import weaviate_pb2_grpc

    has_grpc = True
except ImportError:
    has_grpc = False


Session = Union[requests.sessions.Session, OAuth2Session]
TIMEOUT_TYPE_RETURN = Tuple[NUMBERS, NUMBERS]


class BaseConnection:
    """
    Connection class used to communicate to a weaviate instance.
    """

    def __init__(
        self,
        url: str,
        auth_client_secret: Optional[AuthCredentials],
        timeout_config: TIMEOUT_TYPE_RETURN,
        proxies: Union[dict, str, None],
        trust_env: bool,
        additional_headers: Optional[Dict[str, Any]],
        startup_period: Optional[int],
        connection_config: ConnectionConfig,
        embedded_db: Optional[EmbeddedDB] = None,
        grcp_port: Optional[int] = None,
    ):
        """
        Initialize a Connection class instance.

        Parameters
        ----------
        url : str
            URL to a running weaviate instance.
        auth_client_secret : weaviate.auth.AuthCredentials, optional
            Credentials to authenticate with a weaviate instance. The credentials are not saved within the client and
            authentication is done via authentication tokens.
        timeout_config : tuple(float, float) or float, optional
            Set the timeout configuration for all requests to the Weaviate server. It can be a
            float or, a tuple of two floats: (connect timeout, read timeout).
            If only one float is passed then both connect and read timeout will be set to
            that value.
        proxies : dict, str or None, optional
            Proxies to be used for requests. Are used by both 'requests' and 'aiohttp'. Can be
            passed as a dict ('requests' format:
            https://docs.python-requests.org/en/stable/user/advanced/#proxies), str (HTTP/HTTPS
            protocols are going to use this proxy) or None.
        trust_env : bool, optional
            Whether to read proxies from the ENV variables: (HTTP_PROXY or http_proxy, HTTPS_PROXY
            or https_proxy).
            NOTE: 'proxies' has priority over 'trust_env', i.e. if 'proxies' is NOT None,
            'trust_env' is ignored.
        additional_headers : Dict[str, Any] or None
            Additional headers to include in the requests, used to set OpenAI key. OpenAI key looks
            like this: {'X-OpenAI-Api-Key': 'KEY'}.
        startup_period : int or None
            How long the client will wait for weaviate to start before raising a RequestsConnectionError.
            If None the client will not wait at all.

        Raises
        ------
        ValueError
            If no authentication credentials provided but the Weaviate server has an OpenID
            configured.
        """

        self._api_version_path = "/v1"
        self.url = url  # e.g. http://localhost:80
        self.timeout_config: TIMEOUT_TYPE_RETURN = timeout_config
        self.embedded_db = embedded_db

        self._grpc_stub: Optional[weaviate_pb2_grpc.WeaviateStub] = None

        # create GRPC channel. If weaviate does not support GRPC, fallback to GraphQL is used.
        if has_grpc and grcp_port is not None:
            parsed_url = urlparse(self.url)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                s.settimeout(1.0)  # we're only pinging the port, 1s is plenty
                s.connect((parsed_url.hostname, grcp_port))
                s.shutdown(2)
                s.close()
                channel = grpc.insecure_channel(f"{parsed_url.hostname}:{grcp_port}")
                self._grpc_stub = weaviate_pb2_grpc.WeaviateStub(channel)
            except (
                ConnectionRefusedError,
                TimeoutError,
                socket.timeout,
            ):  # self._grpc_stub stays None
                s.close()

        self._headers = {"content-type": "application/json"}
        if additional_headers is not None:
            if not isinstance(additional_headers, dict):
                raise TypeError(
                    f"'additional_headers' must be of type dict or None. Given type: {type(additional_headers)}."
                )
            for key, value in additional_headers.items():
                self._headers[key.lower()] = value

        self._proxies = _get_proxies(proxies, trust_env)

        # auth secrets can contain more information than a header (refresh tokens and lifetime) and therefore take
        # precedent over headers
        if "authorization" in self._headers and auth_client_secret is not None:
            _Warnings.auth_header_and_auth_secret()
            self._headers.pop("authorization")

        self._session: Session
        self._shutdown_background_event: Optional[Event] = None

        if startup_period is not None:
            _check_positive_num(startup_period, "startup_period", int, include_zero=False)
            self.wait_for_weaviate(startup_period)

        self._create_session(auth_client_secret)
        self._add_adapter_to_session(connection_config)

    def _create_session(self, auth_client_secret: Optional[AuthCredentials]) -> None:
        """Creates a request session.

        Either through authlib.oauth2 if authentication is enabled or a normal request session otherwise.

        Raises
        ------
        ValueError
            If no authentication credentials provided but the Weaviate server has OpenID configured.
        """
        # API keys are separate from OIDC and do not need any config from weaviate
        if auth_client_secret is not None and isinstance(auth_client_secret, AuthApiKey):
            self._headers["authorization"] = "Bearer " + auth_client_secret.api_key
            self._session = requests.Session()
            return

        if "authorization" in self._headers and auth_client_secret is None:
            self._session = requests.Session()
            return

        oidc_url = self.url + self._api_version_path + "/.well-known/openid-configuration"
        response = requests.get(
            oidc_url,
            headers={"content-type": "application/json"},
            timeout=self._timeout_config,
            proxies=self._proxies,
        )
        if response.status_code == 200:
            # Some setups are behind proxies that return some default page - for example a login - for all requests.
            # If the response is not json, we assume that this is the case and try unauthenticated access. Any auth
            # header provided by the user is unaffected.
            try:
                resp = response.json()
            except JSONDecodeError:
                _Warnings.auth_cannot_parse_oidc_config(oidc_url)
                self._session = requests.Session()
                return

            if auth_client_secret is not None and not isinstance(auth_client_secret, AuthApiKey):
                _auth = _Auth(resp, auth_client_secret, self)
                self._session = _auth.get_auth_session()

                if isinstance(auth_client_secret, AuthClientCredentials):
                    # credentials should only be saved for client credentials, otherwise use refresh token
                    self._create_background_token_refresh(_auth)
                else:
                    self._create_background_token_refresh()
            else:
                msg = f""""No login credentials provided. The weaviate instance at {self.url} requires login credentials.

                    Please check our documentation at https://weaviate.io/developers/weaviate/client-libraries/python#authentication
                    for more information about how to use authentication."""

                if is_weaviate_domain(self.url):
                    msg += """

                    You can instantiate the client with login credentials for WCS using

                    client = weaviate.Client(
                      url=YOUR_WEAVIATE_URL,
                      auth_client_secret=weaviate.AuthClientPassword(
                        username = YOUR_WCS_USER,
                        password = YOUR_WCS_PW,
                      ))
                    """
                raise AuthenticationFailedException(msg)
        elif response.status_code == 404 and auth_client_secret is not None:
            _Warnings.auth_with_anon_weaviate()
            self._session = requests.Session()
        else:
            self._session = requests.Session()

    def get_current_bearer_token(self) -> str:
        if "authorization" in self._headers:
            return self._headers["authorization"]
        elif isinstance(self._session, OAuth2Session):
            return "Bearer " + self._session.token["access_token"]

        return ""

    def _add_adapter_to_session(self, connection_config: ConnectionConfig):
        adapter = HTTPAdapter(
            pool_connections=connection_config.session_pool_connections,
            pool_maxsize=connection_config.session_pool_maxsize,
        )
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

    def _create_background_token_refresh(self, _auth: Optional[_Auth] = None):
        """Create a background thread that periodically refreshes access and refresh tokens.

        While the underlying library refreshes tokens, it does not have an internal cronjob that checks every
        X-seconds if a token has expired. If there is no activity for longer than the refresh tokens lifetime, it will
        expire. Therefore, refresh manually shortly before expiration time is up."""
        if "refresh_token" not in self._session.token and _auth is None:
            return

        expires_in: int = self._session.token.get(
            "expires_in", 60
        )  # use 1minute as token lifetime if not supplied
        self._shutdown_background_event = Event()

        def periodic_refresh_token(refresh_time: int, _auth: Optional[_Auth]):
            time.sleep(max(refresh_time - 30, 1))
            while not self._shutdown_background_event.is_set():
                # use refresh token when available
                try:
                    if "refresh_token" in self._session.token:
                        assert isinstance(self._session, OAuth2Session)
                        self._session.token = self._session.refresh_token(
                            self._session.metadata["token_endpoint"]
                        )
                        refresh_time = self._session.token.get("expires_in") - 30
                    else:
                        # client credentials usually does not contain a refresh token => get a new token using the
                        # saved credentials
                        assert _auth is not None
                        new_session = _auth.get_auth_session()
                        self._session.token = new_session.fetch_token()
                except (RequestsHTTPError, ReadTimeout) as exc:
                    # retry again after one second, might be an unstable connection
                    refresh_time = 1
                    _Warnings.token_refresh_failed(exc)

                time.sleep(max(refresh_time, 1))

        demon = Thread(
            target=periodic_refresh_token,
            args=(expires_in, _auth),
            daemon=True,
            name="TokenRefresh",
        )
        demon.start()

    def close(self):
        """Shutdown connection class gracefully."""
        # in case an exception happens before definition of these members
        if (
            hasattr(self, "_shutdown_background_event")
            and self._shutdown_background_event is not None
        ):
            self._shutdown_background_event.set()
        if hasattr(self, "_session"):
            self._session.close()

    def _get_request_header(self) -> dict:
        """
        Returns the correct headers for a request.

        Returns
        -------
        dict
            Request header as a dict.
        """
        return self._headers

    def delete(
        self,
        path: str,
        weaviate_object: dict = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        """
        Make a DELETE request to the Weaviate server instance.

        Parameters
        ----------
        path : str
            Sub-path to the Weaviate resources. Must be a valid Weaviate sub-path.
            e.g. '/meta' or '/objects', without version.
        weaviate_object : dict, optional
            Object is used as payload for DELETE request. By default None.
        params : dict, optional
            Additional request parameters, by default None

        Returns
        -------
        requests.Response
            The response, if request was successful.

        Raises
        ------
        requests.ConnectionError
            If the DELETE request could not be made.
        """
        if self.embedded_db is not None:
            self.embedded_db.ensure_running()
        request_url = self.url + self._api_version_path + path

        return self._session.delete(
            url=request_url,
            json=weaviate_object,
            headers=self._get_request_header(),
            timeout=self._timeout_config,
            proxies=self._proxies,
            params=params,
        )

    def patch(
        self,
        path: str,
        weaviate_object: dict,
        params: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        """
        Make a PATCH request to the Weaviate server instance.

        Parameters
        ----------
        path : str
            Sub-path to the Weaviate resources. Must be a valid Weaviate sub-path.
            e.g. '/meta' or '/objects', without version.
        weaviate_object : dict
            Object is used as payload for PATCH request.
        params : dict, optional
            Additional request parameters, by default None
        Returns
        -------
        requests.Response
            The response, if request was successful.

        Raises
        ------
        requests.ConnectionError
            If the PATCH request could not be made.
        """
        if self.embedded_db is not None:
            self.embedded_db.ensure_running()
        request_url = self.url + self._api_version_path + path

        return self._session.patch(
            url=request_url,
            json=weaviate_object,
            headers=self._get_request_header(),
            timeout=self._timeout_config,
            proxies=self._proxies,
            params=params,
        )

    def post(
        self,
        path: str,
        weaviate_object: dict,
        params: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        """
        Make a POST request to the Weaviate server instance.

        Parameters
        ----------
        path : str
            Sub-path to the Weaviate resources. Must be a valid Weaviate sub-path.
            e.g. '/meta' or '/objects', without version.
        weaviate_object : dict
            Object is used as payload for POST request.
        params : dict, optional
            Additional request parameters, by default None
        external_url: Is an external (non-weaviate) url called

        Returns
        -------
        requests.Response
            The response, if request was successful.

        Raises
        ------
        requests.ConnectionError
            If the POST request could not be made.
        """
        if self.embedded_db is not None:
            self.embedded_db.ensure_running()
        request_url = self.url + self._api_version_path + path

        return self._session.post(
            url=request_url,
            json=weaviate_object,
            headers=self._get_request_header(),
            timeout=self._timeout_config,
            proxies=self._proxies,
            params=params,
        )

    def put(
        self,
        path: str,
        weaviate_object: dict,
        params: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        """
        Make a PUT request to the Weaviate server instance.

        Parameters
        ----------
        path : str
            Sub-path to the Weaviate resources. Must be a valid Weaviate sub-path.
            e.g. '/meta' or '/objects', without version.
        weaviate_object : dict
            Object is used as payload for PUT request.
        params : dict, optional
            Additional request parameters, by default None
        Returns
        -------
        requests.Response
            The response, if request was successful.

        Raises
        ------
        requests.ConnectionError
            If the PUT request could not be made.
        """
        if self.embedded_db is not None:
            self.embedded_db.ensure_running()
        request_url = self.url + self._api_version_path + path

        return self._session.put(
            url=request_url,
            json=weaviate_object,
            headers=self._get_request_header(),
            timeout=self._timeout_config,
            proxies=self._proxies,
            params=params,
        )

    def get(
        self, path: str, params: Optional[Dict[str, Any]] = None, external_url: bool = False
    ) -> requests.Response:
        """Make a GET request.

        Parameters
        ----------
        path : str
            Sub-path to the Weaviate resources. Must be a valid Weaviate sub-path.
            e.g. '/meta' or '/objects', without version.
        params : dict, optional
            Additional request parameters, by default None
        external_url: Is an external (non-weaviate) url called

        Returns
        -------
        requests.Response
            The response if request was successful.

        Raises
        ------
        requests.ConnectionError
            If the GET request could not be made.
        """
        if self.embedded_db is not None:
            self.embedded_db.ensure_running()
        if params is None:
            params = {}

        if external_url:
            request_url = path
        else:
            request_url = self.url + self._api_version_path + path

        return self._session.get(
            url=request_url,
            headers=self._get_request_header(),
            timeout=self._timeout_config,
            params=params,
            proxies=self._proxies,
        )

    def head(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        """
        Make a HEAD request to the server.

        Parameters
        ----------
        path : str
            Sub-path to the resources. Must be a valid sub-path.
            e.g. '/meta' or '/objects', without version.
        params : dict, optional
            Additional request parameters, by default None

        Returns
        -------
        requests.Response
            The response to the request.

        Raises
        ------
        requests.ConnectionError
            If the HEAD request could not be made.
        """
        if self.embedded_db is not None:
            self.embedded_db.ensure_running()
        request_url = self.url + self._api_version_path + path

        return self._session.head(
            url=request_url,
            headers=self._get_request_header(),
            timeout=self._timeout_config,
            proxies=self._proxies,
            params=params,
        )

    @property
    def timeout_config(self) -> TIMEOUT_TYPE_RETURN:
        """
        Getter/setter for `timeout_config`.

        Parameters
        ----------
        timeout_config : tuple(float, float), optional
            For Setter only: Set the timeout configuration for all requests to the Weaviate server.
            It can be a float or, a tuple of two floats:
                    (connect timeout, read timeout).
            If only one float is passed then both connect and read timeout will be set to
            that value.

        Returns
        -------
        Tuple[float, float]
            For Getter only: Requests Timeout configuration.
        """

        return self._timeout_config

    @timeout_config.setter
    def timeout_config(self, timeout_config: TIMEOUT_TYPE_RETURN):
        """
        Setter for `timeout_config`. (docstring should be only in the Getter)
        """

        self._timeout_config = timeout_config

    @property
    def proxies(self) -> dict:
        return self._proxies

    def wait_for_weaviate(self, startup_period: Optional[int]):
        """
        Waits until weaviate is ready or the timelimit given in 'startup_period' has passed.

        Parameters
        ----------
        startup_period : Optional[int]
            Describes how long the client will wait for weaviate to start in seconds.

        Raises
        ------
        WeaviateStartUpError
            If weaviate takes longer than the timelimit to respond.
        """

        ready_url = self.url + self._api_version_path + "/.well-known/ready"
        for _i in range(startup_period):
            try:
                requests.get(ready_url).raise_for_status()
                return
            except (RequestsHTTPError, RequestsConnectionError):
                time.sleep(1)

        try:
            requests.get(ready_url).raise_for_status()
            return
        except (RequestsHTTPError, RequestsConnectionError) as error:
            raise WeaviateStartUpError(
                f"Weaviate did not start up in {startup_period} seconds. Either the Weaviate URL {self.url} is wrong or Weaviate did not start up in the interval given in 'startup_period'."
            ) from error


class Connection(BaseConnection):
    def __init__(
        self,
        url: str,
        auth_client_secret: Optional[AuthCredentials],
        timeout_config: TIMEOUT_TYPE_RETURN,
        proxies: Union[dict, str, None],
        trust_env: bool,
        additional_headers: Optional[Dict[str, Any]],
        startup_period: Optional[int],
        connection_config: ConnectionConfig,
        embedded_db: Optional[EmbeddedDB] = None,
        grcp_port: Optional[int] = None,
    ):
        super().__init__(
            url,
            auth_client_secret,
            timeout_config,
            proxies,
            trust_env,
            additional_headers,
            startup_period,
            connection_config,
            embedded_db,
            grcp_port,
        )
        self._server_version = self.get_meta()["version"]
        if self._server_version < "1.14":
            _Warnings.weaviate_server_older_than_1_14(self._server_version)

    @property
    def grpc_stub(self) -> Optional[weaviate_pb2_grpc.WeaviateStub]:
        return self._grpc_stub

    @property
    def server_version(self) -> str:
        """
        Version of the weaviate instance.
        """
        return self._server_version

    def get_meta(self) -> Dict[str, str]:
        """
        Returns the meta endpoint.
        """
        response = self.get(path="/meta")
        if response.status_code == 200:
            return response.json()
        raise UnexpectedStatusCodeException("Meta endpoint", response)


def _get_epoch_time() -> int:
    """
    Get the current epoch time as an integer.

    Returns
    -------
    int
        Current epoch time.
    """

    dts = datetime.datetime.utcnow()
    return round(time.mktime(dts.timetuple()) + dts.microsecond / 1e6)


def _get_proxies(proxies: Union[dict, str, None], trust_env: bool) -> dict:
    """
    Get proxies as dict, compatible with 'requests' library.
    NOTE: 'proxies' has priority over 'trust_env', i.e. if 'proxies' is NOT None, 'trust_env'
    is ignored.

    Parameters
    ----------
    proxies : dict, str or None
        The proxies to use for requests. If it is a dict it should follow 'requests' library
        format (https://docs.python-requests.org/en/stable/user/advanced/#proxies). If it is
        a URL (str), a dict will be constructed with both 'http' and 'https' pointing to that
        URL. If None, no proxies will be used.
    trust_env : bool
        If True, the proxies will be read from ENV VARs (case insensitive):
            HTTP_PROXY/HTTPS_PROXY.
        NOTE: It is ignored if 'proxies' is NOT None.

    Returns
    -------
    dict
        A dictionary with proxies, either set from 'proxies' or read from ENV VARs.
    """

    if proxies is not None:
        if isinstance(proxies, str):
            return {
                "http": proxies,
                "https": proxies,
            }
        if isinstance(proxies, dict):
            return proxies
        raise TypeError(
            "If 'proxies' is not None, it must be of type dict or str. "
            f"Given type: {type(proxies)}."
        )

    if not trust_env:
        return {}

    http_proxy = (os.environ.get("HTTP_PROXY"), os.environ.get("http_proxy"))
    https_proxy = (os.environ.get("HTTPS_PROXY"), os.environ.get("https_proxy"))

    if not any(http_proxy + https_proxy):
        return {}

    proxies = {}
    if any(http_proxy):
        proxies["http"] = http_proxy[0] if http_proxy[0] else http_proxy[1]
    if any(https_proxy):
        proxies["https"] = https_proxy[0] if https_proxy[0] else https_proxy[1]

    return proxies
