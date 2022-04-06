"""
Connection class definition.
"""
import datetime
import time
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
            auth_client_secret: Optional[AuthCredentials]=None,
            timeout_config: Union[Tuple[Real, Real], Real]=(2, 20)
        ):
        """
        Initialize a Connection class instance.

        Parameters
        ----------
        url : str
            URL to a running weaviate instance.
        auth_client_secret : weaviate.auth.AuthCredentials, optional
            User login credentials to a weaviate instance, by default None
        timeout_config : tuple(Real, Real) or Real, optional
            Set the timeout configuration for all requests to the Weaviate server. It can be a
            real number or, a tuple of two real numbers: (connect timeout, read timeout).
            If only one real number is passed then both connect and read timeout will be set to
            that value, by default (2, 20).

        Raises
        ------
        ValueError
            If no authentication credentials provided but the Weaviate server has an OpenID
            configured.
        """

        self._api_version_path = '/v1'
        self._session = requests.Session()
        self.url = url  # e.g. http://localhost:80
        self._timeout_config = timeout_config # this uses the setter

        self._auth_expires = 0  # unix time when auth expires
        self._auth_bearer = None
        self._auth_client_secret = auth_client_secret

        self._is_authentication_required = False

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
            timeout=self._timeout_config
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
            If the grant_types supported by the thirdparty authentication service are insufficient.
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
                    timeout=(30, 45)
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
                timeout=(30, 45)
                )
        except RequestException as error:
            raise AuthenticationFailedException(
                "Can't connect to the third party authentication service. "
                "Check that it is running.") from error
        if request_third_part.status_code != 200:
            raise AuthenticationFailedException(
                "Status not OK in connection to the third party authentication service.")

        # Validate third part auth info
        if 'client_credentials' not in request_third_part.json()['grant_types_supported']:
            raise AuthenticationFailedException(
                "The grant_types supported by the thirdparty authentication service are "
                "insufficient. Please add 'client_credentials'.")

        request_body = self._auth_client_secret.get_credentials()
        request_body["client_id"] = client_id

        # try the request
        try:
            request = requests.post(
                request_third_part.json()['token_endpoint'],
                request_body,
                timeout=(30, 45)
                )
        except RequestException:
            raise AuthenticationFailedException(
                "Unable to get a OAuth token from server. Are the credentials "
                "and URLs correct?") from None

        # sleep to process
        time.sleep(0.125)

        if request.status_code == 401:
            raise AuthenticationFailedException(
                "Authentication access denied. Are the credentials correct?"
            )
        self._auth_bearer = request.json()['access_token']
        # -2 for some lagtime
        self._auth_expires = int(_get_epoch_time() + request.json()['expires_in'] - 2)

    def _get_request_header(self) -> dict:
        """
        Returns the correct headers for a request.

        Returns
        -------
        dict
            Request header as a dict.
        """

        header = {"content-type": "application/json"}

        if self._is_authentication_required:
            self._refresh_authentication()
            header["Authorization"] = "Bearer " + self._auth_bearer

        return header

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
            timeout=self._timeout_config
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
            timeout=self._timeout_config
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
            timeout=self._timeout_config
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
            timeout=self._timeout_config
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

        )

    @property
    def timeout_config(self) -> Tuple[Real, Real]:
        """
        Getter/setter for `timeout_config`.

        Parameters
        ----------
        timeout_config : tuple(Real, Real) or Real, optional
            For Getter only: Set the timeout configuration for all requests to the Weaviate server.
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
