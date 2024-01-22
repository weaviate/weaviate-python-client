from __future__ import annotations

from typing import Dict, Generic, List, Type, TypeVar, Union, cast
from typing import TYPE_CHECKING

import requests
from authlib.integrations.httpx_client import OAuth2Client  # type: ignore
from authlib.integrations.requests_client import OAuth2Session  # type: ignore

from weaviate.auth import (
    AuthCredentials,
    AuthClientPassword,
    AuthBearerToken,
    AuthClientCredentials,
)
from weaviate.exceptions import MissingScopeError, AuthenticationFailedError
from ..util import _decode_json_response_dict
from ..warnings import _Warnings

if TYPE_CHECKING:
    from .base import _ConnectionBase

AUTH_DEFAULT_TIMEOUT = 5
OIDC_CONFIG = Dict[str, Union[str, List[str]]]


T = TypeVar("T", bound=Union[OAuth2Client, OAuth2Session])


class _Auth(Generic[T]):
    def __init__(
        self,
        session_type: Type[T],
        oidc_config: OIDC_CONFIG,
        credentials: AuthCredentials,
        connection: _ConnectionBase,
    ) -> None:
        self._credentials: AuthCredentials = credentials
        self._connection = connection
        self.__session_type: Type[T] = session_type
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
                raise AuthenticationFailedError(
                    """Microsoft/azure does not recommend to authenticate using username and password and this method is
                    not supported by the python client."""
                )

            # The grant_types_supported field is optional and does not have to be present in the response
            if (
                "grant_types_supported" in oidc_config
                and "password" not in oidc_config["grant_types_supported"]
            ):
                raise AuthenticationFailedError(
                    """The grant_types supported by the third-party authentication service are insufficient. Please add
                    the 'password' grant type."""
                )

    def _get_token_endpoint(self) -> str:
        response_auth = requests.get(
            self._open_id_config_url, proxies=self._connection.get_proxies()
        )
        response_auth_json = _decode_json_response_dict(response_auth, "Get token endpoint")
        assert response_auth_json is not None
        token_endpoint = response_auth_json["token_endpoint"]
        assert isinstance(token_endpoint, str)
        return token_endpoint

    def get_auth_session(self) -> T:
        if isinstance(self._credentials, AuthBearerToken):
            sessions = self._get_session_auth_bearer_token(self._credentials)
        elif isinstance(self._credentials, AuthClientCredentials):
            sessions = self._get_session_client_credential(self._credentials)
        else:
            assert isinstance(self._credentials, AuthClientPassword)
            sessions = self._get_session_user_pw(self._credentials)

        return sessions

    def _get_session_auth_bearer_token(self, config: AuthBearerToken) -> T:
        token: Dict[str, Union[str, int]] = {"access_token": config.access_token}
        if config.expires_in is not None:
            token["expires_in"] = config.expires_in
        if config.refresh_token is not None:
            token["refresh_token"] = config.refresh_token

        if "refresh_token" not in token:
            _Warnings.auth_no_refresh_token(config.expires_in)

        return cast(
            T,
            self.__session_type(
                token=token,
                token_endpoint=self._token_endpoint,
                client_id=self._client_id,
                default_timeout=AUTH_DEFAULT_TIMEOUT,
            ),
        )

    def _get_session_user_pw(self, config: AuthClientPassword) -> T:
        scope: List[str] = self._default_scopes.copy()
        scope.extend(config.scope_list)
        session = self.__session_type(
            client_id=self._client_id,
            token_endpoint=self._token_endpoint,
            grant_type="password",
            scope=scope,
            default_timeout=AUTH_DEFAULT_TIMEOUT,
        )
        token = session.fetch_token(username=config.username, password=config.password)
        if "refresh_token" not in token:
            _Warnings.auth_no_refresh_token(token["expires_in"])

        return cast(T, session)

    def _get_session_client_credential(self, config: AuthClientCredentials) -> T:
        scope: List[str] = self._default_scopes.copy()

        if config.scope_list is not None:
            scope.extend(config.scope_list)
        if len(scope) == 0:
            # hardcode commonly used scopes
            if self._token_endpoint.startswith("https://login.microsoftonline.com"):
                scope = [self._client_id + "/.default"]
            else:
                raise MissingScopeError

        session = self.__session_type(
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
        session.fetch_token()
        return cast(T, session)
