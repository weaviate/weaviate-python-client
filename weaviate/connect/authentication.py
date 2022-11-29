from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Tuple, Dict

import requests
from authlib.integrations.requests_client import OAuth2Session
from requests import RequestException

from weaviate.auth import (
    AuthCredentials,
    AuthClientPassword,
    AuthBearerConfig,
    AuthClientCredentials,
)
from weaviate.exceptions import MissingScopeException, AuthenticationFailedException

if TYPE_CHECKING:
    from . import Connection


class _Auth:
    def __init__(
        self, response: Dict[str, str], auth_config: AuthCredentials, connection: Connection
    ) -> None:
        self._auth_config: AuthCredentials = auth_config
        self._connection: Connection = connection

        self._open_id_config_url: str = response["href"]
        self._client_id: str = response["clientId"]

        self._token_endpoint: str = self._get_token_endpoint()
        self._validate(response)

    def _validate(self, response: Dict[str, str]) -> None:
        if isinstance(self._auth_config, AuthClientPassword):
            if self._token_endpoint.startswith("https://login.microsoftonline.com"):
                raise AuthenticationFailedException(
                    """Microsoft/azure does not recommend to authenticate using username and password and this method is
                    not supported by the python client."""
                )

            # The grant_types_supported field is optional and does not have to be present in the response
            if (
                "grant_types_supported" in response
                and "password" not in response["grant_types_supported"]
            ):
                raise AuthenticationFailedException(
                    """The grant_types supported by the third-party authentication service are insufficient. Please add
                    the 'password' grant type."""
                )

    def _get_token_endpoint(self) -> str:
        response_auth = self._connection.get(self._open_id_config_url, external_url=True)
        return response_auth.json()["token_endpoint"]

    def get_auth_token(self) -> Tuple[str, int]:
        if isinstance(self._auth_config, AuthBearerConfig):
            return self._auth_config.bearer_token, 1
        elif isinstance(self._auth_config, AuthClientCredentials):
            return self._get_token_client_credential(self._token_endpoint, self._auth_config)
        else:
            assert isinstance(self._auth_config, AuthClientPassword)
            return self._get_token_user_pw(self._token_endpoint, self._auth_config)

    def _get_token_user_pw(self, token_endpoint: str, config: AuthClientPassword):
        request_body = {
            "grant_type": "password",
            "client_id": self._client_id,
            "username": config.username,
            "password": config.password,
        }
        try:
            request = requests.post(
                token_endpoint,
                request_body,
                proxies=self._connection.proxies,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        except RequestException:
            raise AuthenticationFailedException(
                "Unable to get a OAuth token from server. Are the credentials and URLs correct?"
            )
        if request.status_code == 401:
            raise AuthenticationFailedException(
                "Authentication access denied. Are the credentials correct?"
            )
        token = request.json()
        return token["access_token"], token["expires_in"]

    def _get_token_client_credential(self, token_endpoint: str, config: AuthClientCredentials):
        if config.scope is not None:
            scope = config.scope
        else:
            # hardcode commonly used scopes
            if token_endpoint.startswith("https://login.microsoftonline.com"):
                scope = self._client_id + "/.default"
            else:
                raise MissingScopeException

        session = OAuth2Session(
            client_id=self._client_id,
            client_secret=config.client_secret,
            token_endpoint_auth_method="client_secret_post",
            scope=scope,
            token_endpoint=token_endpoint,
            grant_type="client_credentials",
            token={"access_token": None, "expires_in": -100},
        )
        token = session.fetch_token()
        return token["access_token"], token["expires_in"]
