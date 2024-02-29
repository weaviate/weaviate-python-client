from __future__ import annotations

import time
from copy import copy
from dataclasses import dataclass, field
from threading import Thread, Event
from typing import Any, Dict, List, Literal, Optional, Tuple, Union, cast, overload

from authlib.integrations.httpx_client import AsyncOAuth2Client, OAuth2Client  # type: ignore
from grpc import _channel, Channel  # type: ignore
from grpc.aio import Channel as AsyncChannel  # type: ignore
from grpc_health.v1 import health_pb2  # type: ignore
from httpx import (
    AsyncClient,
    AsyncHTTPTransport,
    Client,
    ConnectError,
    HTTPError,
    Limits,
    ReadError,
    RemoteProtocolError,
    RequestError,
    Response,
    HTTPTransport,
    get,
    Timeout,
)

from weaviate import __version__ as client_version
from weaviate.auth import (
    AuthCredentials,
    AuthApiKey,
    AuthClientCredentials,
)
from weaviate.config import ConnectionConfig, Proxies, Timeout as TimeoutConfig
from weaviate.connect.authentication import _Auth
from weaviate.connect.base import (
    _ConnectionBase,
    ConnectionParams,
    JSONPayload,
    _get_proxies,
)
from weaviate.embedded import EmbeddedV4
from weaviate.exceptions import (
    AuthenticationFailedError,
    UnexpectedStatusCodeError,
    WeaviateGRPCUnavailableError,
    WeaviateStartUpError,
    WeaviateClosedClientError,
    WeaviateConnectionError,
)
from weaviate.proto.v1 import weaviate_pb2_grpc
from weaviate.util import (
    is_weaviate_domain,
    is_weaviate_client_too_old,
    PYPI_PACKAGE_URL,
    _decode_json_response_dict,
    _ServerVersion,
)
from weaviate.validator import _ValidateArgument, _validate_input
from weaviate.warnings import _Warnings

Session = Union[Client, OAuth2Client]
AsyncSession = Union[AsyncClient, AsyncOAuth2Client]


@dataclass
class _ExpectedStatusCodes:
    ok_in: Union[List[int], int]
    error: str
    ok: List[int] = field(init=False)

    def __post_init__(self) -> None:
        if isinstance(self.ok_in, int):
            self.ok = [self.ok_in]
        else:
            self.ok = self.ok_in


class _Connection(_ConnectionBase):
    """
    Connection class used to communicate to a weaviate instance.
    """

    def __init__(
        self,
        connection_params: ConnectionParams,
        auth_client_secret: Optional[AuthCredentials],
        timeout_config: TimeoutConfig,
        proxies: Union[str, Proxies, None],
        trust_env: bool,
        additional_headers: Optional[Dict[str, Any]],
        connection_config: ConnectionConfig,
        embedded_db: Optional[EmbeddedV4] = None,
    ):
        self.url = connection_params._http_url
        self.embedded_db = embedded_db
        self._api_version_path = "/v1"
        self._aclient: Optional[AsyncSession] = None
        self._client: Session
        self.__additional_headers = {}
        self._auth = auth_client_secret
        self._connection_params = connection_params
        self._grpc_stub: Optional[weaviate_pb2_grpc.WeaviateStub] = None
        self._grpc_stub_async: Optional[weaviate_pb2_grpc.WeaviateStub] = None
        self._grpc_channel: Optional[Channel] = None
        self._grpc_channel_async: Optional[AsyncChannel] = None
        self.timeout_config = timeout_config
        self.__connection_config = connection_config
        self.__trust_env = trust_env
        self._weaviate_version = _ServerVersion.from_string("")
        self.__connected = False

        self._headers = {"content-type": "application/json"}
        if additional_headers is not None:
            _validate_input(_ValidateArgument([dict], "additional_headers", additional_headers))
            self.__additional_headers = additional_headers
            for key, value in additional_headers.items():
                self._headers[key.lower()] = value

        self._proxies: Dict[str, str] = _get_proxies(proxies, trust_env)

        # auth secrets can contain more information than a header (refresh tokens and lifetime) and therefore take
        # precedent over headers
        if "authorization" in self._headers and auth_client_secret is not None:
            _Warnings.auth_header_and_auth_secret()
            self._headers.pop("authorization")

        # if there are API keys included add them right away to headers
        if auth_client_secret is not None and isinstance(auth_client_secret, AuthApiKey):
            self._headers["authorization"] = "Bearer " + auth_client_secret.api_key

    def connect(self, skip_init_checks: bool) -> None:
        if self.embedded_db is not None:
            self.embedded_db.start()
        self._create_clients(self._auth, skip_init_checks)
        self.__connected = True

        # need this to get the version of weaviate for version checks
        try:
            self._weaviate_version = _ServerVersion.from_string(self.get_meta()["version"])
        except (WeaviateConnectionError, ReadError, RemoteProtocolError) as e:
            raise WeaviateStartUpError(f"Could not connect to Weaviate:{e}.") from e

        if not skip_init_checks:
            try:
                pkg_info = get(PYPI_PACKAGE_URL, timeout=self.timeout_config.init).json()
                pkg_info = pkg_info.get("info", {})
                latest_version = pkg_info.get("version", "unknown version")
                if is_weaviate_client_too_old(client_version, latest_version):
                    _Warnings.weaviate_client_too_old_vs_latest(client_version, latest_version)
            except RequestError:
                pass  # ignore any errors related to requests, it is a best-effort warning

    def is_connected(self) -> bool:
        return self.__connected

    @overload
    def __make_mounts(self, type_: Literal["sync"]) -> Dict[str, HTTPTransport]:
        ...

    @overload
    def __make_mounts(self, type_: Literal["async"]) -> Dict[str, AsyncHTTPTransport]:
        ...

    def __make_mounts(
        self, type_: Literal["sync", "async"]
    ) -> Union[Dict[str, HTTPTransport], Dict[str, AsyncHTTPTransport]]:
        if type_ == "async":
            return {
                f"{key}://"
                if key == "http" or key == "https"
                else key: AsyncHTTPTransport(
                    limits=Limits(
                        max_connections=self.__connection_config.session_pool_maxsize,
                        max_keepalive_connections=self.__connection_config.session_pool_connections,
                    ),
                    proxy=proxy,
                    retries=self.__connection_config.session_pool_max_retries,
                    trust_env=self.__trust_env,
                )
                for key, proxy in self._proxies.items()
                if key != "grpc"
            }
        else:
            assert type_ == "sync"
            return {
                f"{key}://"
                if key == "http" or key == "https"
                else key: HTTPTransport(
                    limits=Limits(
                        max_connections=self.__connection_config.session_pool_maxsize,
                        max_keepalive_connections=self.__connection_config.session_pool_connections,
                    ),
                    proxy=proxy,
                    retries=self.__connection_config.session_pool_max_retries,
                    trust_env=self.__trust_env,
                )
                for key, proxy in self._proxies.items()
                if key != "grpc"
            }

    def __make_sync_client(self) -> Client:
        return Client(
            headers=self._headers,
            timeout=Timeout(
                None, connect=self.timeout_config.query, read=self.timeout_config.insert
            ),
            mounts=self.__make_mounts("sync"),
        )

    def __make_async_client(self) -> AsyncClient:
        return AsyncClient(
            headers=self._headers,
            timeout=Timeout(
                None, connect=self.timeout_config.query, read=self.timeout_config.insert
            ),
            mounts=self.__make_mounts("async"),
        )

    def __make_clients(self) -> None:
        self._client = self.__make_sync_client()

    def _create_clients(
        self, auth_client_secret: Optional[AuthCredentials], skip_init_checks: bool
    ) -> None:
        # API keys are separate from OIDC and do not need any config from weaviate
        if auth_client_secret is not None and isinstance(auth_client_secret, AuthApiKey):
            self.__make_clients()
            return

        if "authorization" in self._headers and auth_client_secret is None:
            self.__make_clients()
            return

        # no need to check OIDC if no auth is provided and users dont want any checks at initialization time
        if skip_init_checks and auth_client_secret is None:
            self.__make_clients()
            return

        oidc_url = self.url + self._api_version_path + "/.well-known/openid-configuration"
        with self.__make_sync_client() as client:
            response = client.get(oidc_url)
        if response.status_code == 200:
            # Some setups are behind proxies that return some default page - for example a login - for all requests.
            # If the response is not json, we assume that this is the case and try unauthenticated access. Any auth
            # header provided by the user is unaffected.
            try:
                resp = response.json()
            except Exception:
                _Warnings.auth_cannot_parse_oidc_config(oidc_url)
                self.__make_clients()
                return

            if auth_client_secret is not None:
                _auth = _Auth(
                    session_type=OAuth2Client,
                    oidc_config=resp,
                    credentials=auth_client_secret,
                    connection=self,
                )
                try:
                    self._client = _auth.get_auth_session()
                except HTTPError as e:
                    raise AuthenticationFailedError(f"Failed to authenticate with OIDC: {repr(e)}")

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

                    client = weaviate.connect_to_wcs(
                      url=YOUR_WEAVIATE_URL,
                      auth_client_secret=wvc.init.Auth.api_key("YOUR_API_KEY")
                    )
                    """
                raise AuthenticationFailedError(msg)
        elif response.status_code == 404 and auth_client_secret is not None:
            _Warnings.auth_with_anon_weaviate()
            self.__make_clients()
        else:
            self.__make_clients()

    def get_current_bearer_token(self) -> str:
        if not self.is_connected():
            raise WeaviateClosedClientError()

        if "authorization" in self._headers:
            return self._headers["authorization"]
        elif isinstance(self._client, OAuth2Client):
            return f"Bearer {self._client.token['access_token']}"
        return ""

    def _create_background_token_refresh(self, _auth: Optional[_Auth] = None) -> None:
        """Create a background thread that periodically refreshes access and refresh tokens.

        While the underlying library refreshes tokens, it does not have an internal cronjob that checks every
        X-seconds if a token has expired. If there is no activity for longer than the refresh tokens lifetime, it will
        expire. Therefore, refresh manually shortly before expiration time is up."""
        assert isinstance(self._client, OAuth2Client)
        if "refresh_token" not in self._client.token and _auth is None:
            return

        expires_in: int = self._client.token.get(
            "expires_in", 60
        )  # use 1minute as token lifetime if not supplied
        self._shutdown_background_event = Event()

        def periodic_refresh_token(refresh_time: int, _auth: Optional[_Auth[OAuth2Client]]) -> None:
            time.sleep(max(refresh_time - 30, 1))
            while (
                self._shutdown_background_event is not None
                and not self._shutdown_background_event.is_set()
            ):
                # use refresh token when available
                try:
                    if "refresh_token" in cast(OAuth2Client, self._client).token:
                        assert isinstance(self._client, OAuth2Client)
                        self._client.token = self._client.refresh_token(
                            self._client.metadata["token_endpoint"]
                        )
                        expires_in = self._client.token.get("expires_in", 60)
                        assert isinstance(expires_in, int)
                        refresh_time = expires_in - 30
                    else:
                        # client credentials usually does not contain a refresh token => get a new token using the
                        # saved credentials
                        assert _auth is not None
                        assert isinstance(self._client, OAuth2Client)
                        new_session = _auth.get_auth_session()
                        self._client.token = new_session.fetch_token()
                except HTTPError as exc:
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

    async def aopen(self) -> None:
        if self._aclient is None:
            self._aclient = self.__make_async_client()
        if self._grpc_stub_async is None:
            self._grpc_channel_async = self._connection_params._grpc_channel(
                async_channel=True, proxies=self._proxies
            )
            assert self._grpc_channel_async is not None
            self._grpc_stub_async = weaviate_pb2_grpc.WeaviateStub(self._grpc_channel_async)

    async def aclose(self) -> None:
        if self._aclient is not None:
            await self._aclient.aclose()
            self._aclient = None
        if self._grpc_stub_async is not None:
            assert self._grpc_channel_async is not None
            await self._grpc_channel_async.close()
            self._grpc_stub_async = None

    def close(self) -> None:
        """Shutdown connection class gracefully."""
        # in case an exception happens before definition of these members
        if (
            hasattr(self, "_shutdown_background_event")
            and self._shutdown_background_event is not None
        ):
            self._shutdown_background_event.set()

        if hasattr(self, "_client"):
            self._client.close()
        if self._grpc_channel is not None:
            self._grpc_channel.close()
        if self.embedded_db is not None:
            self.embedded_db.stop()
        self.__connected = False

    def __get_latest_headers(self) -> Dict[str, str]:
        if "authorization" in self._headers:
            return self._headers

        auth_token = self.get_current_bearer_token()
        if auth_token == "":
            return self._headers

        # bearer token can change over time (OIDC) so we need to get the current one for each request
        copied_headers = copy(self._headers)
        copied_headers.update({"authorization": self.get_current_bearer_token()})
        return copied_headers

    def __send(
        self,
        method: Literal["DELETE", "GET", "HEAD", "PATCH", "POST", "PUT"],
        url: str,
        error_msg: str,
        status_codes: Optional[_ExpectedStatusCodes],
        weaviate_object: Optional[JSONPayload] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Response:
        if not self.is_connected():
            raise WeaviateClosedClientError()
        if self.embedded_db is not None:
            self.embedded_db.ensure_running()
        try:
            req = self._client.build_request(
                method,
                url,
                json=weaviate_object,
                params=params,
                headers=self.__get_latest_headers(),
            )
            res = self._client.send(req)
            if status_codes is not None and res.status_code not in status_codes.ok:
                raise UnexpectedStatusCodeError(error_msg, response=res)
            return cast(Response, res)
        except RuntimeError as e:
            raise WeaviateClosedClientError() from e
        except ConnectError as conn_err:
            raise WeaviateConnectionError(error_msg) from conn_err

    def delete(
        self,
        path: str,
        weaviate_object: Optional[JSONPayload] = None,
        params: Optional[Dict[str, Any]] = None,
        error_msg: str = "",
        status_codes: Optional[_ExpectedStatusCodes] = None,
    ) -> Response:
        return self.__send(
            "DELETE",
            url=self.url + self._api_version_path + path,
            weaviate_object=weaviate_object,
            params=params,
            error_msg=error_msg,
            status_codes=status_codes,
        )

    def patch(
        self,
        path: str,
        weaviate_object: JSONPayload,
        params: Optional[Dict[str, Any]] = None,
        error_msg: str = "",
        status_codes: Optional[_ExpectedStatusCodes] = None,
    ) -> Response:
        return self.__send(
            "PATCH",
            url=self.url + self._api_version_path + path,
            weaviate_object=weaviate_object,
            params=params,
            error_msg=error_msg,
            status_codes=status_codes,
        )

    def post(
        self,
        path: str,
        weaviate_object: JSONPayload,
        params: Optional[Dict[str, Any]] = None,
        error_msg: str = "",
        status_codes: Optional[_ExpectedStatusCodes] = None,
    ) -> Response:
        return self.__send(
            "POST",
            url=self.url + self._api_version_path + path,
            weaviate_object=weaviate_object,
            params=params,
            error_msg=error_msg,
            status_codes=status_codes,
        )

    async def apost(
        self,
        path: str,
        weaviate_object: JSONPayload,
        params: Optional[Dict[str, Any]] = None,
    ) -> Response:
        if not self.is_connected():
            raise WeaviateClosedClientError()
        assert self._aclient is not None

        if self.embedded_db is not None:
            self.embedded_db.ensure_running()
        request_url = self.url + self._api_version_path + path

        return await self._aclient.post(
            url=request_url,
            json=weaviate_object,
            params=params,
            headers=self.__get_latest_headers(),
        )

    def put(
        self,
        path: str,
        weaviate_object: JSONPayload,
        params: Optional[Dict[str, Any]] = None,
        error_msg: str = "",
        status_codes: Optional[_ExpectedStatusCodes] = None,
    ) -> Response:
        return self.__send(
            "PUT",
            url=self.url + self._api_version_path + path,
            weaviate_object=weaviate_object,
            params=params,
            error_msg=error_msg,
            status_codes=status_codes,
        )

    def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        error_msg: str = "",
        status_codes: Optional[_ExpectedStatusCodes] = None,
    ) -> Response:
        if self.embedded_db is not None:
            self.embedded_db.ensure_running()
        if params is None:
            params = {}

        request_url = self.url + self._api_version_path + path

        return self.__send(
            "GET", url=request_url, params=params, error_msg=error_msg, status_codes=status_codes
        )

    def head(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        error_msg: str = "",
        status_codes: Optional[_ExpectedStatusCodes] = None,
    ) -> Response:
        return self.__send(
            "HEAD",
            url=self.url + self._api_version_path + path,
            params=params,
            error_msg=error_msg,
            status_codes=status_codes,
        )

    @property
    def server_version(self) -> str:
        """
        Version of the weaviate instance.
        """
        return str(self._weaviate_version)

    def get_proxies(self) -> dict:
        return self._proxies

    @property
    def additional_headers(self) -> Dict[str, str]:
        return self.__additional_headers

    def get_meta(self) -> Dict[str, str]:
        """
        Returns the meta endpoint.
        """
        response = self.get(path="/meta")
        res = _decode_json_response_dict(response, "Meta endpoint")
        assert res is not None
        return res


class ConnectionV4(_Connection):
    def __init__(
        self,
        connection_params: ConnectionParams,
        auth_client_secret: Optional[AuthCredentials],
        timeout_config: TimeoutConfig,
        proxies: Union[str, Proxies, None],
        trust_env: bool,
        additional_headers: Optional[Dict[str, Any]],
        connection_config: ConnectionConfig,
        embedded_db: Optional[EmbeddedV4] = None,
    ):
        super().__init__(
            connection_params,
            auth_client_secret,
            timeout_config,
            proxies,
            trust_env,
            additional_headers,
            connection_config,
            embedded_db,
        )
        self.__prepare_grpc_headers()

    def __prepare_grpc_headers(self) -> None:
        self.__metadata_list: List[Tuple[str, str]] = []
        if len(self.additional_headers):
            for key, val in self.additional_headers.items():
                if val is not None:
                    self.__metadata_list.append((key.lower(), val))

        if self._auth is not None:
            if isinstance(self._auth, AuthApiKey):
                self.__metadata_list.append(("authorization", self._auth.api_key))
            else:
                self.__metadata_list.append(
                    ("authorization", "dummy_will_be_refreshed_for_each_call")
                )

        if len(self.__metadata_list) > 0:
            self.__grpc_headers: Optional[Tuple[Tuple[str, str], ...]] = tuple(self.__metadata_list)
        else:
            self.__grpc_headers = None

    def grpc_headers(self) -> Optional[Tuple[Tuple[str, str], ...]]:
        if self._auth is None or not isinstance(self._auth, AuthApiKey):
            return self.__grpc_headers

        assert self.__grpc_headers is not None
        access_token = self.get_current_bearer_token()
        # auth is last entry in list, rest is static
        self.__metadata_list[len(self.__metadata_list) - 1] = ("authorization", access_token)
        return tuple(self.__metadata_list)

    def _ping_grpc(self) -> None:
        """Performs a grpc health check and raises WeaviateGRPCUnavailableError if not."""
        if not self.is_connected():
            raise WeaviateClosedClientError()
        assert self._grpc_channel is not None
        try:
            res: health_pb2.HealthCheckResponse = self._grpc_channel.unary_unary(
                "/grpc.health.v1.Health/Check",
                request_serializer=health_pb2.HealthCheckRequest.SerializeToString,
                response_deserializer=health_pb2.HealthCheckResponse.FromString,
            )(health_pb2.HealthCheckRequest(), timeout=self.timeout_config.init)
            if res.status != health_pb2.HealthCheckResponse.SERVING:
                raise WeaviateGRPCUnavailableError(f"v{self.server_version}")
        except _channel._InactiveRpcError as e:
            raise WeaviateGRPCUnavailableError(f"v{self.server_version}") from e

    def connect(self, skip_init_checks: bool) -> None:
        super().connect(skip_init_checks)
        # create GRPC channel. If Weaviate does not support GRPC then error now.
        self._grpc_channel = self._connection_params._grpc_channel(
            async_channel=False, proxies=self._proxies
        )
        assert self._grpc_channel is not None
        self._grpc_stub = weaviate_pb2_grpc.WeaviateStub(self._grpc_channel)
        if not skip_init_checks:
            self._ping_grpc()

        # do it after all other init checks so as not to break all the tests
        if self._weaviate_version.is_lower_than(1, 23, 7):
            raise WeaviateStartUpError(
                f"Weaviate version {self._weaviate_version} is not supported. Please use Weaviate version 1.23.7 or higher."
            )

    @property
    def grpc_stub(self) -> Optional[weaviate_pb2_grpc.WeaviateStub]:
        if not self.is_connected():
            raise WeaviateClosedClientError()
        return self._grpc_stub

    @property
    def agrpc_stub(self) -> Optional[weaviate_pb2_grpc.WeaviateStub]:
        if not self.is_connected():
            raise WeaviateClosedClientError()
        return self._grpc_stub_async
