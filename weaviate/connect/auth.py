from __future__ import annotations

from typing import Dict, List, Union

from httpx import get
from authlib.integrations.httpx_client import AsyncOAuth2Client, OAuth2Client  # type: ignore

from weaviate.auth import (
    AuthCredentials,
    AuthClientPassword,
    AuthBearerToken,
    AuthClientCredentials,
)
from weaviate.connect.base import _ConnectionBase
from weaviate.exceptions import (
    MissingScopeException,
    AuthenticationFailedException,
)
from weaviate.util import _decode_json_response_dict
from weaviate.warnings import _Warnings

AUTH_DEFAULT_TIMEOUT = 5
OIDC_CONFIG = Dict[str, Union[str, List[str]]]


class _Auth:
    def __init__(
        self,
        oidc_config: OIDC_CONFIG,
        credentials: AuthCredentials,
        connection: _ConnectionBase,
    ) -> None:
        self._credentials: AuthCredentials = credentials
        self._connection: _ConnectionBase = connection
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
        response_auth = get(self._open_id_config_url, proxies=self._connection.get_proxies())
        response_auth_json = _decode_json_response_dict(response_auth, "Get token endpoint")
        assert response_auth_json is not None
        token_endpoint = response_auth_json["token_endpoint"]
        assert isinstance(token_endpoint, str)
        return token_endpoint

    def get_sync_auth_client(self) -> OAuth2Client:
        if isinstance(self._credentials, AuthBearerToken):
            session = self._get_client_auth_bearer_token(self._credentials)
        elif isinstance(self._credentials, AuthClientCredentials):
            session = self._get_client_client_credential(self._credentials)
        else:
            assert isinstance(self._credentials, AuthClientPassword)
            session = self._get_client_user_pw(self._credentials)

        return session

    async def get_async_auth_client(self) -> AsyncOAuth2Client:
        if isinstance(self._credentials, AuthBearerToken):
            session = await self._get_aclient_auth_bearer_token(self._credentials)
        elif isinstance(self._credentials, AuthClientCredentials):
            session = await self._get_aclient_client_credential(self._credentials)
        else:
            assert isinstance(self._credentials, AuthClientPassword)
            session = await self._get_aclient_user_pw(self._credentials)

        return session

    def _get_client_auth_bearer_token(self, config: AuthBearerToken) -> OAuth2Client:
        token: Dict[str, Union[str, int]] = {"access_token": config.access_token}
        if config.expires_in is not None:
            token["expires_in"] = config.expires_in
        if config.refresh_token is not None:
            token["refresh_token"] = config.refresh_token

        if "refresh_token" not in token:
            _Warnings.auth_no_refresh_token(config.expires_in)

        # token endpoint and clientId are needed for token refresh
        return OAuth2Client(
            token=token,
            token_endpoint=self._token_endpoint,
            client_id=self._client_id,
            default_timeout=AUTH_DEFAULT_TIMEOUT,
        )

    def _get_aclient_auth_bearer_token(self, config: AuthBearerToken) -> AsyncOAuth2Client:
        token: Dict[str, Union[str, int]] = {"access_token": config.access_token}
        if config.expires_in is not None:
            token["expires_in"] = config.expires_in
        if config.refresh_token is not None:
            token["refresh_token"] = config.refresh_token

        if "refresh_token" not in token:
            _Warnings.auth_no_refresh_token(config.expires_in)

        # token endpoint and clientId are needed for token refresh
        return AsyncOAuth2Client(
            token=token,
            token_endpoint=self._token_endpoint,
            client_id=self._client_id,
            default_timeout=AUTH_DEFAULT_TIMEOUT,
        )

    def _get_client_user_pw(self, config: AuthClientPassword) -> OAuth2Client:
        scope: List[str] = self._default_scopes.copy()
        scope.extend(config.scope_list)
        session = OAuth2Client(
            client_id=self._client_id,
            token_endpoint=self._token_endpoint,
            grant_type="password",
            scope=scope,
            default_timeout=AUTH_DEFAULT_TIMEOUT,
        )
        token = session.fetch_token(username=config.username, password=config.password)
        if "refresh_token" not in token:
            _Warnings.auth_no_refresh_token(token["expires_in"])

        return session

    async def _get_aclient_user_pw(self, config: AuthClientPassword) -> AsyncOAuth2Client:
        scope: List[str] = self._default_scopes.copy()
        scope.extend(config.scope_list)
        session = AsyncOAuth2Client(
            client_id=self._client_id,
            token_endpoint=self._token_endpoint,
            grant_type="password",
            scope=scope,
            default_timeout=AUTH_DEFAULT_TIMEOUT,
        )
        token = await session._fetch_token(username=config.username, password=config.password)
        if "refresh_token" not in token:
            _Warnings.auth_no_refresh_token(token["expires_in"])

        return session

    def _get_client_client_credential(self, config: AuthClientCredentials) -> OAuth2Client:
        scope: List[str] = self._default_scopes.copy()

        if config.scope_list is not None:
            scope.extend(config.scope_list)
        if len(scope) == 0:
            # hardcode commonly used scopes
            if self._token_endpoint.startswith("https://login.microsoftonline.com"):
                scope = [self._client_id + "/.default"]
            else:
                raise MissingScopeException

        session = OAuth2Client(
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
        return session

    async def _get_aclient_client_credential(
        self, config: AuthClientCredentials
    ) -> AsyncOAuth2Client:
        scope: List[str] = self._default_scopes.copy()

        if config.scope_list is not None:
            scope.extend(config.scope_list)
        if len(scope) == 0:
            # hardcode commonly used scopes
            if self._token_endpoint.startswith("https://login.microsoftonline.com"):
                scope = [self._client_id + "/.default"]
            else:
                raise MissingScopeException

        session = AsyncOAuth2Client(
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
        await session._fetch_token()
        return session
