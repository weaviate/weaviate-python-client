"""
Connection class definition.
"""
import os
import time
import datetime
from typing import Tuple, Optional, Union
from numbers import Real
import requests
from requests import RequestException
from weaviate.exceptions import AuthenticationFailedException
from weaviate.auth import AuthCredentials
from weaviate.util import _get_valid_timeout_config


class Connection:
    """
    Connection class used to communicate to a weaviate instance.
    """
    def __init__(self,
            url: str,
            auth_client_secret: Optional[AuthCredentials],
            timeout_config: Union[Tuple[Real, Real], Real],
            proxies: Union[dict, str, None],
            trust_env: bool,
            additional_headers: Optional[dict],
        ):
        """
        Initialize a Connection class instance.

        Parameters
        ----------
        url : str
            URL to a running weaviate instance.
        auth_client_secret : weaviate.auth.AuthCredentials, optional
            User login credentials to a weaviate instance.
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
        additional_headers : dict or None
            Additional headers to include in the requests, used to set OpenAI key. OpenAI key looks
            like this: {'X-OpenAI-Api-Key': 'KEY'}.

        Raises
        ------
        ValueError
            If no authentication credentials provided but the Weaviate server has an OpenID
            configured.
        """

        self._api_version_path = '/v1'
        self._server_version = None
        self._session = requests.Session()
        self.url = url  # e.g. http://localhost:80
        self._timeout_config = timeout_config # this uses the setter

        self._auth_expires = 0  # unix time when auth expires
        self._auth_bearer = None
        self._auth_client_secret = auth_client_secret

        self._is_authentication_required = False

        self._headers = {"content-type": "application/json"}
        if additional_headers is not None:
            if not isinstance(additional_headers, dict):
                raise TypeError(
                    "'additional_headers' must be of type dict or None. "
                    f"Given type: {type(additional_headers)}."
                )
            self._headers.update(additional_headers)

        self._proxies = _get_proxies(proxies, trust_env)

        self._log_in()

    def _log_in(self) -> None:
        """
        Log in to the Weaviate server only if the Weaviate server has an OpenID configured.

        Raises
        ------
        ValueError
            If no authentication credentials provided but the Weaviate server has an OpenID
            configured.
        """

        response = self._session.get(
            self.url + self._api_version_path + "/.well-known/openid-configuration",
            headers={"content-type": "application/json"},
            timeout=self._timeout_config,
            proxies=self._proxies,
        )

        if response.status_code == 200:
            if isinstance(self._auth_client_secret, AuthCredentials):
                self._is_authentication_required = True
                self._refresh_authentication()
            else:
                raise ValueError(
                    "No login credentials provided. The weaviate instance at "
                    f"{self.url} requires login credential, use argument 'auth_client_secret'."
                )

    def __del__(self):
        """
        Destructor for Connection class instance.
        """

        self._session.close()

    # Requests a new bearer
    def _refresh_authentication(self) -> None:
        """
        Request a new bearer.

        Raises
        ------
        weaviate.AuthenticationFailedException
            If cannot connect to weaviate.
        weaviate.AuthenticationFailedException
            If cannot authenticate http status not ok.
        weaviate.AuthenticationFailedException
            If cannot connect to the third party authentication service.
        weaviate.AuthenticationFailedException
            If status not OK in connection to the third party authentication service.
        weaviate.AuthenticationFailedException
            If grant_types supported by the third-party authentication service are insufficient.
        weaviate.AuthenticationFailedException
            If unable to get a OAuth token from server.
        weaviate.AuthenticationFailedException
            If authentication access denied.
        """

        if self._auth_expires < _get_epoch_time():
            # collect data for the request
            try:
                request = self._session.get(
                    self.url + self._api_version_path + "/.well-known/openid-configuration",
                    headers={"content-type": "application/json"},
                    timeout=(30, 45),
                    proxies=self._proxies,
                )
            except RequestException as error:
                raise AuthenticationFailedException("Cannot connect to weaviate.") from error
            if request.status_code != 200:
                raise AuthenticationFailedException("Cannot authenticate http status not ok.")

            # Set the client ID
            client_id = request.json()['clientId']

            self._set_bearer(client_id=client_id, href=request.json()['href'])

    def _set_bearer(self, client_id: str, href: str) -> None:
        """
        Set bearer for a refreshed authentication.

        Parameters
        ----------
        client_id : str
            The client ID of the OpenID Connect.
        href : str
            The URL of the OpenID Connect issuer.

        Raises
        ------
        weaviate.AuthenticationFailedException
            If authentication failed.
        """

        # request additional information
        try:
            request_third_part = requests.get(
                href,
                headers={"content-type": "application/json"},
                timeout=(30, 45),
                proxies=self._proxies,
            )
        except RequestException as error:
            raise AuthenticationFailedException(
                "Can't connect to the third party authentication service. "
                "Check that it is running."
            ) from error
        if request_third_part.status_code != 200:
            raise AuthenticationFailedException(
                "Status not OK in connection to the third party authentication service."
            )

        # Validate third part auth info
        if 'client_credentials' not in request_third_part.json()['grant_types_supported']:
            raise AuthenticationFailedException(
                "The grant_types supported by the third-party authentication service are "
                "insufficient. Please add 'client_credentials'."
            )

        request_body = self._auth_client_secret.get_credentials()
        request_body["client_id"] = client_id

        # try the request
        try:
            request = requests.post(
                request_third_part.json()['token_endpoint'],
                request_body,
                timeout=(30, 45),
                proxies=self._proxies,
            )
        except RequestException:
            raise AuthenticationFailedException(
                "Unable to get a OAuth token from server. Are the credentials "
                "and URLs correct?"
            ) from None

        # sleep to process
        time.sleep(0.125)

        if request.status_code == 401:
            raise AuthenticationFailedException(
                "Authentication access denied. Are the credentials correct?"
            )
        self._auth_bearer = request.json()['access_token']
        # -2 for some lag time
        self._auth_expires = int(_get_epoch_time() + request.json()['expires_in'] - 2)

    def _get_request_header(self) -> dict:
        """
        Returns the correct headers for a request.

        Returns
        -------
        dict
            Request header as a dict.
        """

        if self._is_authentication_required:
            self._refresh_authentication()
            self._headers["Authorization"] = "Bearer " + self._auth_bearer
        return self._headers

    def delete(self,
            path: str,
            weaviate_object: dict=None,
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

    def patch(self,
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

    def post(self,
            path: str,
            weaviate_object: dict,
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

        Returns
        -------
        requests.Response
            The response, if request was successful.

        Raises
        ------
        requests.ConnectionError
            If the POST request could not be made.
        """

        request_url = self.url + self._api_version_path + path

        return self._session.post(
            url=request_url,
            json=weaviate_object,
            headers=self._get_request_header(),
            timeout=self._timeout_config,
            proxies=self._proxies,
        )

    def put(self,
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

    def get(self,
            path: str,
            params: dict=None,
        ) -> requests.Response:
        """
        Make a GET request to the Weaviate server instance.

        Parameters
        ----------
        path : str
            Sub-path to the Weaviate resources. Must be a valid Weaviate sub-path.
            e.g. '/meta' or '/objects', without version.
        params : dict, optional
            Additional request parameters, by default None

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
    def server_version(self) -> Tuple[Real, Real]:
        """
        Getter/setter for Weaviate `server_version`.

        Parameters
        ----------
        server_version : str
            For Setter only: The Weaviate server version gotten from the `Client.get_meta()`.

        Returns
        -------
        str
            For Getter only: Weaviate server version.
        """

        return self._server_version

    @server_version.setter
    def server_version(self, server_version: Union[Tuple[Real, Real], Real]):
        """
        Setter for `server_version`. (docstring should be only in the Getter)
        """

        if not isinstance(server_version, str):
            raise TypeError(
                f"'server_version' must be of type str. Given type: {type(server_version)}."
            )

        self._server_version = server_version


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
                'http': proxies,
                'https': proxies,
            }
        if isinstance(proxies, dict):
            return proxies
        raise TypeError(
            "If 'proxies' is not None, it must be of type dict or str. "
            f"Given type: {type(proxies)}."
        )

    if not trust_env:
        return {}

    http_proxy = (os.environ.get('HTTP_PROXY'), os.environ.get('http_proxy'))
    https_proxy = (os.environ.get('HTTPS_PROXY'), os.environ.get('https_proxy'))

    if not any(http_proxy + https_proxy):
        return {}

    proxies = {}
    if any(http_proxy):
        proxies['http'] = http_proxy[0] if http_proxy[0] else http_proxy[1]
    if any(https_proxy):
        proxies['https'] = https_proxy[0] if https_proxy[0] else https_proxy[1]

    return proxies
