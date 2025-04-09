from __future__ import annotations

from typing import Awaitable, Callable, Dict, List, Optional, Union

import httpx
from authlib.integrations.httpx_client import OAuth2Client, AsyncOAuth2Client  # type: ignore

from weaviate.auth import (
    AuthCredentials,
    AuthClientPassword,
    AuthBearerToken,
    AuthClientCredentials,
)
from weaviate.exceptions import MissingScopeError, AuthenticationFailedError
from . import executor
from ..util import _decode_json_response_dict
from ..warnings import _Warnings

AUTH_DEFAULT_TIMEOUT = 5
OIDC_CONFIG = Dict[str, Union[str, List[str]]]

Result = Union[OAuth2Client, Awaitable[AsyncOAuth2Client]]
MountsMaker = Union[
    Callable[[], Dict[str, httpx.AsyncHTTPTransport]], Callable[[], Dict[str, httpx.HTTPTransport]]
]


class _Auth:
    def __init__(
        self,
        oidc_config: OIDC_CONFIG,
        credentials: AuthCredentials,
        make_mounts: MountsMaker,
        colour: executor.Colour,
    ) -> None:
        self._credentials: AuthCredentials = credentials
        self.__make_mounts = make_mounts
        self.__colour: executor.Colour = colour
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

    @staticmethod
    def result(result: Result) -> OAuth2Client:
        assert isinstance(result, OAuth2Client)
        return result

    @staticmethod
    async def aresult(result: Result) -> AsyncOAuth2Client:
        assert isinstance(result, Awaitable)
        return await result

    @staticmethod
    def use(
        oidc_config: OIDC_CONFIG,
        credentials: AuthCredentials,
        make_mounts: MountsMaker,
        colour: executor.Colour,
    ) -> executor.Result[_Auth]:
        auth = _Auth(oidc_config, credentials, make_mounts, colour)
        if colour == "async":

            async def _execute() -> _Auth:
                auth._token_endpoint = await executor.aresult(auth._get_token_endpoint())
                await executor.aresult(auth._validate(auth._oidc_config))
                return auth

            return _execute()
        auth._token_endpoint = executor.result(auth._get_token_endpoint())
        executor.result(auth._validate(auth._oidc_config))
        return auth

    def _validate(self, oidc_config: OIDC_CONFIG) -> executor.Result[None]:
        if isinstance(self._credentials, AuthClientPassword):
            # The grant_types_supported field is optional and does not have to be present in the response
            if (
                "grant_types_supported" in oidc_config
                and "password" not in oidc_config["grant_types_supported"]
            ):
                raise AuthenticationFailedError(
                    """The grant_types supported by the third-party authentication service are insufficient. Please add
                    the 'password' grant type."""
                )

            def resp(res: str) -> None:
                if res.startswith("https://login.microsoftonline.com"):
                    raise AuthenticationFailedError(
                        """Microsoft/azure does not recommend to authenticate using username and password and this method is
                        not supported by the python client."""
                    )

            return executor.execute(response_callback=resp, method=self._get_token_endpoint)
        return executor.empty(self.__colour)

    def _get_token_endpoint(self) -> executor.Result[str]:
        if self._token_endpoint is not None:
            return executor.return_(self._token_endpoint, self.__colour)

        def resp(res: httpx.Response) -> str:
            data = _decode_json_response_dict(res, "Get token endpoint")
            assert data is not None
            token_endpoint = data["token_endpoint"]
            assert isinstance(token_endpoint, str)
            return token_endpoint

        if self.__colour == "async":

            async def _execute() -> str:
                mounts: Dict[str, httpx.AsyncBaseTransport] = {}
                for key, mount in self.__make_mounts().items():
                    assert isinstance(mount, httpx.AsyncHTTPTransport)
                    mounts[key] = mount
                async with httpx.AsyncClient(mounts=mounts) as client:
                    return resp(await client.get(self._open_id_config_url))

            return _execute()
        mounts: Dict[str, httpx.BaseTransport] = {}
        for key, mount in self.__make_mounts().items():
            assert isinstance(mount, httpx.BaseTransport)
            mounts[key] = mount
        with httpx.Client(mounts=mounts) as client:
            return resp(client.get(self._open_id_config_url))

    def get_auth_session(self) -> Result:
        if isinstance(self._credentials, AuthBearerToken):
            sessions = self._get_session_auth_bearer_token(self._credentials)
        elif isinstance(self._credentials, AuthClientCredentials):
            sessions = self._get_session_client_credential(self._credentials)
        else:
            assert isinstance(self._credentials, AuthClientPassword)
            sessions = self._get_session_user_pw(self._credentials)
        return sessions

    def _get_session_auth_bearer_token(self, config: AuthBearerToken) -> Result:
        token: Dict[str, Union[str, int]] = {"access_token": config.access_token}
        if config.expires_in is not None:
            token["expires_in"] = config.expires_in
        if config.refresh_token is not None:
            token["refresh_token"] = config.refresh_token

        if "refresh_token" not in token:
            _Warnings.auth_no_refresh_token(config.expires_in)

        if self.__colour == "async":

            async def _execute() -> AsyncOAuth2Client:
                return AsyncOAuth2Client(
                    token=token,
                    token_endpoint=await executor.aresult(self._get_token_endpoint()),
                    client_id=self._client_id,
                    default_timeout=AUTH_DEFAULT_TIMEOUT,
                )

            return _execute()
        return OAuth2Client(
            token=token,
            token_endpoint=executor.result(self._get_token_endpoint()),
            client_id=self._client_id,
            default_timeout=AUTH_DEFAULT_TIMEOUT,
        )

    def _get_session_user_pw(self, config: AuthClientPassword) -> Result:
        scope: List[str] = self._default_scopes.copy()
        scope.extend(config.scope_list)
        if self.__colour == "async":

            async def _execute() -> AsyncOAuth2Client:
                session = AsyncOAuth2Client(
                    client_id=self._client_id,
                    token_endpoint=await executor.aresult(self._get_token_endpoint()),
                    grant_type="password",
                    scope=scope,
                    default_timeout=AUTH_DEFAULT_TIMEOUT,
                )
                token: dict = await session.fetch_token(
                    username=config.username, password=config.password
                )
                if "refresh_token" not in token:
                    _Warnings.auth_no_refresh_token(token["expires_in"])

                return session

            return _execute()
        session = OAuth2Client(
            client_id=self._client_id,
            token_endpoint=executor.result(self._get_token_endpoint()),
            grant_type="password",
            scope=scope,
            default_timeout=AUTH_DEFAULT_TIMEOUT,
        )
        token: dict = session.fetch_token(username=config.username, password=config.password)
        if "refresh_token" not in token:
            _Warnings.auth_no_refresh_token(token["expires_in"])

        return session

    def __get_common_scopes(self) -> executor.Result[List[str]]:
        def resp(res: str) -> List[str]:
            if res.startswith("https://login.microsoftonline.com"):
                return [self._client_id + "/.default"]
            raise MissingScopeError

        return executor.execute(response_callback=resp, method=self._get_token_endpoint)

    def _get_session_client_credential(self, config: AuthClientCredentials) -> Result:
        scope: List[str] = self._default_scopes.copy()

        if config.scope_list is not None:
            scope.extend(config.scope_list)

        if self.__colour == "async":

            async def _execute() -> AsyncOAuth2Client:
                session = AsyncOAuth2Client(
                    client_id=self._client_id,
                    client_secret=config.client_secret,
                    token_endpoint_auth_method="client_secret_post",
                    scope=(
                        scope
                        if len(scope) > 0
                        else await executor.aresult(self.__get_common_scopes())
                    ),
                    token_endpoint=self._token_endpoint,
                    grant_type="client_credentials",
                    token={"access_token": None, "expires_in": -100},
                    default_timeout=AUTH_DEFAULT_TIMEOUT,
                )
                # explicitly fetch tokens. Otherwise, authlib will do it in the background and we might have race-conditions
                await session.fetch_token()
                return session

            return _execute()
        session = OAuth2Client(
            client_id=self._client_id,
            client_secret=config.client_secret,
            token_endpoint_auth_method="client_secret_post",
            scope=scope if len(scope) > 0 else executor.result(self.__get_common_scopes()),
            token_endpoint=self._token_endpoint,
            grant_type="client_credentials",
            token={"access_token": None, "expires_in": -100},
            default_timeout=AUTH_DEFAULT_TIMEOUT,
        )
        # explicitly fetch tokens. Otherwise, authlib will do it in the background and we might have race-conditions
        session.fetch_token()
        return session
