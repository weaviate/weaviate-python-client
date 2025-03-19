from __future__ import annotations

from typing import Callable, Dict, List, Optional, Union

import httpx
from authlib.integrations.httpx_client import OAuth2Client, AsyncOAuth2Client  # type: ignore

from weaviate.auth import (
    AuthCredentials,
    AuthClientPassword,
    AuthBearerToken,
    AuthClientCredentials,
)
from weaviate.exceptions import MissingScopeError, AuthenticationFailedError
from ..util import _decode_json_response_dict
from ..warnings import _Warnings

AUTH_DEFAULT_TIMEOUT = 5
OIDC_CONFIG = Dict[str, Union[str, List[str]]]


class _Auth:
    def __init__(
        self,
        oidc_config: OIDC_CONFIG,
        credentials: AuthCredentials,
        make_async_mounts: Callable[[], Dict[str, httpx.AsyncHTTPTransport]],
        make_sync_mounts: Callable[[], Dict[str, httpx.HTTPTransport]],
        is_async: bool = False,
    ) -> None:
        self._credentials: AuthCredentials = credentials
        self._make_async_mounts: Callable[[], Dict[str, httpx.AsyncHTTPTransport]] = (
            make_async_mounts
        )
        self._make_sync_mounts: Callable[[], Dict[str, httpx.HTTPTransport]] = make_sync_mounts
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

        self._token_endpoint: Optional[str] = None
        self._oidc_config = oidc_config

    @classmethod
    async def use_async(
        cls,
        oidc_config: OIDC_CONFIG,
        credentials: AuthCredentials,
        make_mounts: Callable[[], Dict[str, httpx.AsyncHTTPTransport]],
    ) -> _Auth:
        auth = cls(oidc_config, credentials, make_mounts, lambda: {}, True)
        auth._token_endpoint = await auth._get_token_endpoint()
        await auth._validate(auth._oidc_config)
        return auth

    @classmethod
    def use_sync(
        cls,
        oidc_config: OIDC_CONFIG,
        credentials: AuthCredentials,
        make_mounts: Callable[[], Dict[str, httpx.HTTPTransport]],
    ) -> _Auth:
        auth = cls(oidc_config, credentials, lambda: {}, make_mounts, False)
        auth._token_endpoint = auth._get_token_endpoint()
        auth._validate(auth._oidc_config)
        return auth

    async def _validate_async(self, oidc_config: OIDC_CONFIG) -> None:
        if isinstance(self._credentials, AuthClientPassword):
            if (await self._get_token_endpoint_async()).startswith(
                "https://login.microsoftonline.com"
            ):
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

    def _validate(self, oidc_config: OIDC_CONFIG) -> None:
        if isinstance(self._credentials, AuthClientPassword):
            if (self._get_token_endpoint()).startswith("https://login.microsoftonline.com"):
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

    async def _get_token_endpoint_async(self) -> str:
        if self._token_endpoint is not None:
            return self._token_endpoint
        async with httpx.AsyncClient(mounts=self._make_async_mounts()) as client:
            response_auth = await client.get(self._open_id_config_url)
        response_auth_json = _decode_json_response_dict(response_auth, "Get token endpoint")
        assert response_auth_json is not None
        token_endpoint = response_auth_json["token_endpoint"]
        assert isinstance(token_endpoint, str)
        return token_endpoint

    def _get_token_endpoint(self) -> str:
        if self._token_endpoint is not None:
            return self._token_endpoint
        with httpx.Client(mounts=self._make_sync_mounts()) as client:
            response_auth = client.get(self._open_id_config_url)
        response_auth_json = _decode_json_response_dict(response_auth, "Get token endpoint")
        assert response_auth_json is not None
        token_endpoint = response_auth_json["token_endpoint"]
        assert isinstance(token_endpoint, str)
        return token_endpoint

    async def get_auth_session_async(self) -> AsyncOAuth2Client:
        if isinstance(self._credentials, AuthBearerToken):
            sessions = await self._get_session_auth_bearer_token(self._credentials)
        elif isinstance(self._credentials, AuthClientCredentials):
            sessions = await self._get_session_client_credential(self._credentials)
        else:
            assert isinstance(self._credentials, AuthClientPassword)
            sessions = await self._get_session_user_pw(self._credentials)

        return sessions

    def get_auth_session(self) -> OAuth2Client:
        if isinstance(self._credentials, AuthBearerToken):
            sessions = self._get_session_auth_bearer_token(self._credentials)
        elif isinstance(self._credentials, AuthClientCredentials):
            sessions = self._get_session_client_credential(self._credentials)
        else:
            assert isinstance(self._credentials, AuthClientPassword)
            sessions = self._get_session_user_pw(self._credentials)

        return sessions

    async def _get_session_auth_bearer_token_async(
        self, config: AuthBearerToken
    ) -> AsyncOAuth2Client:
        token: Dict[str, Union[str, int]] = {"access_token": config.access_token}
        if config.expires_in is not None:
            token["expires_in"] = config.expires_in
        if config.refresh_token is not None:
            token["refresh_token"] = config.refresh_token

        if "refresh_token" not in token:
            _Warnings.auth_no_refresh_token(config.expires_in)

        return AsyncOAuth2Client(
            token=token,
            token_endpoint=await self._get_token_endpoint(),
            client_id=self._client_id,
            default_timeout=AUTH_DEFAULT_TIMEOUT,
        )

    def _get_session_auth_bearer_token(self, config: AuthBearerToken) -> OAuth2Client:
        token: Dict[str, Union[str, int]] = {"access_token": config.access_token}
        if config.expires_in is not None:
            token["expires_in"] = config.expires_in
        if config.refresh_token is not None:
            token["refresh_token"] = config.refresh_token

        if "refresh_token" not in token:
            _Warnings.auth_no_refresh_token(config.expires_in)

        return OAuth2Client(
            token=token,
            token_endpoint=self._get_token_endpoint(),
            client_id=self._client_id,
            default_timeout=AUTH_DEFAULT_TIMEOUT,
        )

    async def _get_session_user_pw_async(self, config: AuthClientPassword) -> AsyncOAuth2Client:
        scope: List[str] = self._default_scopes.copy()
        scope.extend(config.scope_list)
        session = AsyncOAuth2Client(
            client_id=self._client_id,
            token_endpoint=await self._get_token_endpoint(),
            grant_type="password",
            scope=scope,
            default_timeout=AUTH_DEFAULT_TIMEOUT,
        )
        token: dict = await session.fetch_token(username=config.username, password=config.password)
        if "refresh_token" not in token:
            _Warnings.auth_no_refresh_token(token["expires_in"])

        return session

    def _get_session_user_pw(self, config: AuthClientPassword) -> OAuth2Client:
        scope: List[str] = self._default_scopes.copy()
        scope.extend(config.scope_list)
        session = OAuth2Client(
            client_id=self._client_id,
            token_endpoint=self._get_token_endpoint(),
            grant_type="password",
            scope=scope,
            default_timeout=AUTH_DEFAULT_TIMEOUT,
        )
        token: dict = session.fetch_token(username=config.username, password=config.password)
        if "refresh_token" not in token:
            _Warnings.auth_no_refresh_token(token["expires_in"])

        return session

    async def _get_session_client_credential_async(
        self, config: AuthClientCredentials
    ) -> AsyncOAuth2Client:
        scope: List[str] = self._default_scopes.copy()

        if config.scope_list is not None:
            scope.extend(config.scope_list)
        if len(scope) == 0:
            # hardcode commonly used scopes
            if (await self._get_token_endpoint()).startswith("https://login.microsoftonline.com"):
                scope = [self._client_id + "/.default"]
            else:
                raise MissingScopeError

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
        await session.fetch_token()
        return session

    def _get_session_client_credential(self, config: AuthClientCredentials) -> OAuth2Client:
        scope: List[str] = self._default_scopes.copy()

        if config.scope_list is not None:
            scope.extend(config.scope_list)
        if len(scope) == 0:
            # hardcode commonly used scopes
            if (self._get_token_endpoint()).startswith("https://login.microsoftonline.com"):
                scope = [self._client_id + "/.default"]
            else:
                raise MissingScopeError

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
