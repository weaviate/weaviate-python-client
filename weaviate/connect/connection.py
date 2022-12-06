"""
Connection class definition.
"""
from __future__ import annotations

import datetime
import os
import time
from numbers import Real
from threading import Thread
from typing import Any, Dict, Tuple, Optional, Union

import requests
from authlib.integrations.requests_client import OAuth2Session

from weaviate import auth
from weaviate.auth import AuthCredentials, AuthClientCredentials
from weaviate.connect.authentication import _Auth
from weaviate.exceptions import AuthenticationFailedException, UnexpectedStatusCodeException
from weaviate.warnings import _Warnings

Session = Union[requests.sessions.Session, OAuth2Session]


class BaseConnection:
    """
    Connection class used to communicate to a weaviate instance.
    """

    def __init__(
        self,
        url: str,
        auth_client_secret: Optional[AuthCredentials],
        timeout_config: Union[Tuple[Real, Real], Real],
        proxies: Union[dict, str, None],
        trust_env: bool,
        additional_headers: Optional[Dict[str, Any]],
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
        timeout_config : tuple(Real, Real) or Real, optional
            Set the timeout configuration for all requests to the Weaviate server. It can be a
            real number or, a tuple of two real numbers: (connect timeout, read timeout).
            If only one real number is passed then both connect and read timeout will be set to
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

        Raises
        ------
        ValueError
            If no authentication credentials provided but the Weaviate server has an OpenID
            configured.
        """

        self._api_version_path = "/v1"
        self.url = url  # e.g. http://localhost:80
        self.timeout_config = timeout_config  # this uses the setter

        self._headers = {"content-type": "application/json"}
        if additional_headers is not None:
            if not isinstance(additional_headers, dict):
                raise TypeError(
                    f"'additional_headers' must be of type dict or None. Given type: {type(additional_headers)}."
                )
            for key, value in additional_headers.items():
                self._headers[key.lower()] = value

        self._proxies = _get_proxies(proxies, trust_env)

        if "authorization" in self._headers:
            bearer_header = self._headers["authorization"]
            auth_client_secret = auth.AuthBearerToken(access_token=bearer_header)

        self._auth: Optional[_Auth] = None
        self._session: Session = self._create_session(auth_client_secret)

        # while the underlying library refreshes tokens, it does not have an internal cronjob that checks every
        # X-seconds if a token has expired. If there is no activity for longer than the refresh tokens lifetime, it will
        # expire. Therefore, refresh manually shortly before expiration time is up.
        if isinstance(self._session, OAuth2Session):
            expires_in = self._session.token.get("expires_in", None)
            if expires_in is not None:

                def periodic_refresh_token():
                    while True:
                        time.sleep(5)
                        if self._auth is not None:
                            # client credentials usually does not contain a refresh token => refresh manually
                            new_session = self._auth.get_auth_session()
                            self._session.token = new_session.fetch_token()
                        else:
                            # use refresh token when
                            self._session.token = self._session.refresh_token(
                                self._session.metadata["token_endpoint"]
                            )

                daemon = Thread(target=periodic_refresh_token, daemon=True, name="TokenRefresh")
                daemon.start()

    def _create_session(self, auth_client_secret: Optional[AuthCredentials]) -> Session:
        """
        Log in to the Weaviate server only if the Weaviate server has an OpenID configured.

        Raises
        ------
        ValueError
            If no authentication credentials provided but the Weaviate server has OpenID configured.
        """
        response = requests.get(
            self.url + self._api_version_path + "/.well-known/openid-configuration",
            headers={"content-type": "application/json"},
            timeout=self._timeout_config,
            proxies=self._proxies,
        )
        if response.status_code == 200:
            if isinstance(auth_client_secret, AuthCredentials):
                resp = response.json()
                _auth = _Auth(resp, auth_client_secret, self)
                if isinstance(auth_client_secret, AuthClientCredentials):
                    self._auth = _auth
                return _auth.get_auth_session()
            else:
                raise AuthenticationFailedException(
                    f""""No login credentials provided. The weaviate instance at {self.url} requires login credential,
                    use argument 'auth_client_secret'."""
                )
        elif response.status_code == 404 and auth_client_secret is not None:
            _Warnings.auth_with_anon_weaviate()
        return requests.Session()

    def __del__(self):
        """
        Destructor for Connection class instance.
        """
        if hasattr(self, "_session"):  # in case an exception happens before session is defined
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

        Returns
        -------
        requests.Response
            The response, if request was successful.

        Raises
        ------
        requests.ConnectionError
            If the DELETE request could not be made.
        """

        request_url = self.url + self._api_version_path + path

        return self._session.delete(
            url=request_url,
            json=weaviate_object,
            headers=self._get_request_header(),
            timeout=self._timeout_config,
            proxies=self._proxies,
        )

    def patch(
        self,
        path: str,
        weaviate_object: dict,
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

        Returns
        -------
        requests.Response
            The response, if request was successful.

        Raises
        ------
        requests.ConnectionError
            If the PATCH request could not be made.
        """

        request_url = self.url + self._api_version_path + path

        return self._session.patch(
            url=request_url,
            json=weaviate_object,
            headers=self._get_request_header(),
            timeout=self._timeout_config,
            proxies=self._proxies,
        )

    def post(
        self,
        path: str,
        weaviate_object: dict,
        external_url: bool = False,
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
        if external_url:
            request_url = path
        else:
            request_url = self.url + self._api_version_path + path

        return self._session.post(
            url=request_url,
            json=weaviate_object,
            headers=self._get_request_header(),
            timeout=self._timeout_config,
            proxies=self._proxies,
        )

    def put(
        self,
        path: str,
        weaviate_object: dict,
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

        Returns
        -------
        requests.Response
            The response, if request was successful.

        Raises
        ------
        requests.ConnectionError
            If the PUT request could not be made.
        """

        request_url = self.url + self._api_version_path + path

        return self._session.put(
            url=request_url,
            json=weaviate_object,
            headers=self._get_request_header(),
            timeout=self._timeout_config,
            proxies=self._proxies,
        )

    def get(self, path: str, params: dict = None, external_url: bool = False) -> requests.Response:
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

    def head(self, path: str) -> requests.Response:
        """
        Make a HEAD request to the server.

        Parameters
        ----------
        path : str
            Sub-path to the resources. Must be a valid sub-path.
            e.g. '/meta' or '/objects', without version.

        Returns
        -------
        requests.Response
            The response to the request.

        Raises
        ------
        requests.ConnectionError
            If the HEAD request could not be made.
        """

        request_url = self.url + self._api_version_path + path

        return self._session.head(
            url=request_url,
            headers=self._get_request_header(),
            timeout=self._timeout_config,
            proxies=self._proxies,
        )

    @property
    def timeout_config(self) -> Tuple[Real, Real]:
        """
        Getter/setter for `timeout_config`.

        Parameters
        ----------
        timeout_config : tuple(Real, Real) or Real, optional
            For Setter only: Set the timeout configuration for all requests to the Weaviate server.
            It can be a real number or, a tuple of two real numbers:
                    (connect timeout, read timeout).
            If only one real number is passed then both connect and read timeout will be set to
            that value.

        Returns
        -------
        Tuple[Real, Real]
            For Getter only: Requests Timeout configuration.
        """

        return self._timeout_config

    @timeout_config.setter
    def timeout_config(self, timeout_config: Union[Tuple[Real, Real], Real]):
        """
        Setter for `timeout_config`. (docstring should be only in the Getter)
        """

        self._timeout_config = _get_valid_timeout_config(timeout_config)

    @property
    def proxies(self) -> dict:
        return self._proxies


class Connection(BaseConnection):
    def __init__(
        self,
        url: str,
        auth_client_secret: Optional[AuthCredentials],
        timeout_config: Union[Tuple[Real, Real], Real],
        proxies: Union[dict, str, None],
        trust_env: bool,
        additional_headers: Optional[Dict[str, Any]],
    ):
        super().__init__(
            url, auth_client_secret, timeout_config, proxies, trust_env, additional_headers
        )
        version = self.get_meta()["version"]
        if version < "1.14":
            _Warnings.weaviate_server_older_than_1_14(version)

    @property
    def server_version(self) -> str:
        """Version of the weaviate instance."""
        return self.get_meta()["version"]

    def get_meta(self) -> Dict[str, str]:
        """Returns the meta endpoint."""
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


def _get_valid_timeout_config(timeout_config: Union[Tuple[Real, Real], Real, None]):
    """
    Validate and return TimeOut configuration.

    Parameters
    ----------
    timeout_config : tuple(Real, Real) or Real or None, optional
            Set the timeout configuration for all requests to the Weaviate server. It can be a
            real number or, a tuple of two real numbers: (connect timeout, read timeout).
            If only one real number is passed then both connect and read timeout will be set to
            that value.

    Raises
    ------
    TypeError
        If arguments are of a wrong data type.
    ValueError
        If 'timeout_config' is not a tuple of 2.
    ValueError
        If 'timeout_config' is/contains negative number/s.
    """

    if isinstance(timeout_config, Real) and not isinstance(timeout_config, bool):
        if timeout_config <= 0.0:
            raise ValueError("'timeout_config' cannot be non-positive number/s!")
        return timeout_config, timeout_config

    if not isinstance(timeout_config, tuple):
        raise TypeError("'timeout_config' should be a (or tuple of) positive real number/s!")
    if len(timeout_config) != 2:
        raise ValueError("'timeout_config' must be of length 2!")
    if not (isinstance(timeout_config[0], Real) and isinstance(timeout_config[1], Real)) or (
        isinstance(timeout_config[0], bool) and isinstance(timeout_config[1], bool)
    ):
        raise TypeError("'timeout_config' must be tuple of real numbers")
    if timeout_config[0] <= 0.0 or timeout_config[1] <= 0.0:
        raise ValueError("'timeout_config' cannot be non-positive number/s!")
    return timeout_config
