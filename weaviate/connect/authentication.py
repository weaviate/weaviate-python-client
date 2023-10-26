from __future__ import annotations

from typing import Dict, List, Tuple, Union
from typing import TYPE_CHECKING

import requests
from authlib.integrations.httpx_client import AsyncOAuth2Client as OAuth2Httpx  # type: ignore
from authlib.integrations.requests_client import OAuth2Session as OAuth2Requests  # type: ignore

from weaviate.auth import (
    AuthCredentials,
    AuthClientPassword,
    AuthBearerToken,
    AuthClientCredentials,
)
from weaviate.exceptions import MissingScopeException, AuthenticationFailedException
from ..util import _decode_json_response_dict
from ..warnings import _Warnings

if TYPE_CHECKING:
    from .connection import Connection

AUTH_DEFAULT_TIMEOUT = 5
OIDC_CONFIG = Dict[str, Union[str, List[str]]]


class _Auth:
    def __init__(
        self,
        oidc_config: OIDC_CONFIG,
        credentials: AuthCredentials,
        connection: Connection,
    ) -> None:
        self._credentials: AuthCredentials = credentials
        self._connection: Connection = connection
        config_url = oidc_config["href"]
        client_id = oidc_config["clientId"]
        assert isinstance(config_url, str) and isinstance(client_id, str)
        self._open_id_config_url: str = config_url
        self._client_id: str = client_id
        self._default_scopes: List[str] = []
        if "scopes" in oidc_config:
            default_scopes = oidc_config["scopes"]
            assert isinstance(default_scopes, list)
            self._default_scopes = default_scopes

        self._token_endpoint: str = self._get_token_endpoint()
        self._validate(oidc_config)

    def _validate(self, oidc_config: OIDC_CONFIG) -> None:
        if isinstance(self._credentials, AuthClientPassword):
            if self._token_endpoint.startswith("https://login.microsoftonline.com"):
                raise AuthenticationFailedException(
                    """Microsoft/azure does not recommend to authenticate using username and password and this method is
                    not supported by the python client."""
                )

            # The grant_types_supported field is optional and does not have to be present in the response
            if (
                "grant_types_supported" in oidc_config
                and "password" not in oidc_config["grant_types_supported"]
            ):
                raise AuthenticationFailedException(
                    """The grant_types supported by the third-party authentication service are insufficient. Please add
                    the 'password' grant type."""
                )

    def _get_token_endpoint(self) -> str:
        response_auth = requests.get(self._open_id_config_url, proxies=self._connection.proxies)
        response_auth_json = _decode_json_response_dict(response_auth, "Get token endpoint")
        assert response_auth_json is not None
        token_endpoint = response_auth_json["token_endpoint"]
        assert isinstance(token_endpoint, str)
        return token_endpoint

    def get_auth_sessions(self) -> Tuple[OAuth2Httpx, OAuth2Requests]:
        if isinstance(self._credentials, AuthBearerToken):
            sessions = self._get_sessions_auth_bearer_token(self._credentials)
        elif isinstance(self._credentials, AuthClientCredentials):
            sessions = self._get_sessions_client_credential(self._credentials)
        else:
            assert isinstance(self._credentials, AuthClientPassword)
            sessions = self._get_sessions_user_pw(self._credentials)

        return sessions

    def _get_sessions_auth_bearer_token(
        self, config: AuthBearerToken
    ) -> Tuple[OAuth2Httpx, OAuth2Requests]:
        token: Dict[str, Union[str, int]] = {"access_token": config.access_token}
        if config.expires_in is not None:
            token["expires_in"] = config.expires_in
        if config.refresh_token is not None:
            token["refresh_token"] = config.refresh_token

        if "refresh_token" not in token:
            _Warnings.auth_no_refresh_token(config.expires_in)

        # token endpoint and clientId are needed for token refresh
        return OAuth2Httpx(
            token=token,
            token_endpoint=self._token_endpoint,
            client_id=self._client_id,
            default_timeout=AUTH_DEFAULT_TIMEOUT,
        ), OAuth2Requests(
            token=token,
            token_endpoint=self._token_endpoint,
            client_id=self._client_id,
            default_timeout=AUTH_DEFAULT_TIMEOUT,
        )

    def _get_sessions_user_pw(
        self, config: AuthClientPassword
    ) -> Tuple[OAuth2Httpx, OAuth2Requests]:
        scope: List[str] = self._default_scopes.copy()
        scope.extend(config.scope_list)
        httpx_ = OAuth2Httpx(
            client_id=self._client_id,
            token_endpoint=self._token_endpoint,
            grant_type="password",
            scope=scope,
            default_timeout=AUTH_DEFAULT_TIMEOUT,
        )
        requests_ = OAuth2Requests(
            client_id=self._client_id,
            token_endpoint=self._token_endpoint,
            grant_type="password",
            scope=scope,
            default_timeout=AUTH_DEFAULT_TIMEOUT,
        )
        httpx_token = httpx_.fetch_token(username=config.username, password=config.password)
        if "refresh_token" not in httpx_token:
            _Warnings.auth_no_refresh_token(httpx_token["expires_in"])
        requests_token = requests_.fetch_token(username=config.username, password=config.password)
        if "refresh_token" not in requests_token:
            _Warnings.auth_no_refresh_token(requests_token["expires_in"])

        return httpx_, requests_

    def _get_sessions_client_credential(
        self, config: AuthClientCredentials
    ) -> Tuple[OAuth2Httpx, OAuth2Requests]:
        scope: List[str] = self._default_scopes.copy()

        if config.scope_list is not None:
            scope.extend(config.scope_list)
        if len(scope) == 0:
            # hardcode commonly used scopes
            if self._token_endpoint.startswith("https://login.microsoftonline.com"):
                scope = [self._client_id + "/.default"]
            else:
                raise MissingScopeException

        httpx_ = OAuth2Httpx(
            client_id=self._client_id,
            client_secret=config.client_secret,
            token_endpoint_auth_method="client_secret_post",
            scope=scope,
            token_endpoint=self._token_endpoint,
            grant_type="client_credentials",
            token={"access_token": None, "expires_in": -100},
            default_timeout=AUTH_DEFAULT_TIMEOUT,
        )
        requests_ = OAuth2Requests(
            client_id=self._client_id,
            client_secret=config.client_secret,
            token_endpoint_auth_method="client_secret_post",
            scope=scope,
            token_endpoint=self._token_endpoint,
            grant_type="client_credentials",
            token={"access_token": None, "expires_in": -100},
            default_timeout=AUTH_DEFAULT_TIMEOUT,
        )
        # explicitly fetch tokens. Otherwise, authlib will do it in the background and we might have race-conditions
        httpx_.fetch_token()
        requests_.fetch_token()
        return httpx_, requests_
