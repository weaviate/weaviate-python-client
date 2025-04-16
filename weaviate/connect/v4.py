from __future__ import annotations

import time
from copy import copy
from dataclasses import dataclass, field
from ssl import SSLZeroReturnError
from threading import Event, Thread
from typing import (
    Any,
    Awaitable,
    Dict,
    List,
    Literal,
    Optional,
    Tuple,
    TypeVar,
    Union,
    cast,
    overload,
)

from authlib.integrations.httpx_client import (  # type: ignore
    AsyncOAuth2Client,
    OAuth2Client,
)
from grpc import Channel as SyncChannel, RpcError, StatusCode, Call  # type: ignore
from grpc.aio import Channel as AsyncChannel, AioRpcError  # type: ignore
from grpc_health.v1 import health_pb2  # type: ignore

# from grpclib.client import Channel
from httpx import (
    AsyncClient,
    AsyncHTTPTransport,
    HTTPTransport,
    Client,
    ConnectError,
    HTTPError,
    HTTPStatusError,
    Limits,
    ReadError,
    ReadTimeout,
    RemoteProtocolError,
    RequestError,
    Response,
    Proxy,
    Timeout,
)

from weaviate import __version__ as client_version
from weaviate.auth import AuthCredentials, AuthApiKey, AuthClientCredentials
from weaviate.config import ConnectionConfig, Proxies, Timeout as TimeoutConfig
from weaviate.connect.authentication import _Auth
from weaviate.connect.base import (
    ConnectionParams,
    JSONPayload,
    _get_proxies,
)
from weaviate.connect import executor
from weaviate.connect.event_loop import _EventLoopSingleton
from weaviate.connect.integrations import _IntegrationConfig
from weaviate.embedded import EmbeddedV4
from weaviate.exceptions import (
    AuthenticationFailedError,
    UnexpectedStatusCodeError,
    WeaviateClosedClientError,
    WeaviateConnectionError,
    WeaviateGRPCUnavailableError,
    WeaviateStartUpError,
    WeaviateTimeoutError,
    InsufficientPermissionsError,
    WeaviateBatchError,
    WeaviateInvalidInputError,
    WeaviateRetryError,
    WeaviateQueryError,
    WeaviateDeleteManyError,
    WeaviateTenantGetError,
)
from weaviate.proto.v1 import (
    aggregate_pb2,
    batch_pb2,
    batch_delete_pb2,
    search_get_pb2,
    tenants_pb2,
    weaviate_pb2_grpc,
)
from weaviate.retry import _Retry
from weaviate.util import (
    PYPI_PACKAGE_URL,
    _decode_json_response_dict,
    _ServerVersion,
    is_weaviate_client_too_old,
    is_weaviate_domain,
)
from weaviate.validator import _validate_input, _ValidateArgument
from weaviate.warnings import _Warnings

Session = Union[Client, OAuth2Client]
AsyncSession = Union[AsyncClient, AsyncOAuth2Client]
HttpClient = Union[AsyncClient, AsyncOAuth2Client, Client, OAuth2Client]

PERMISSION_DENIED = "PERMISSION_DENIED"


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


class _ConnectionBase:
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
        skip_init_checks: bool = False,
    ):
        self.url = connection_params._http_url
        self.embedded_db = embedded_db
        self._api_version_path = "/v1"
        self.__additional_headers = {}
        self._auth = auth_client_secret
        self._client: Optional[HttpClient] = None
        self._connection_params = connection_params
        self._grpc_stub: Optional[weaviate_pb2_grpc.WeaviateStub] = None
        self._grpc_channel: Union[AsyncChannel, SyncChannel, None] = None
        self.timeout_config = timeout_config
        self.__connection_config = connection_config
        self.__trust_env = trust_env
        self._weaviate_version = _ServerVersion.from_string("")
        self._grpc_max_msg_size: Optional[int] = None
        self._connected = False
        self._skip_init_checks = skip_init_checks

        self._headers = {"content-type": "application/json"}
        self.__add_weaviate_embedding_service_header(connection_params.http.host)
        if additional_headers is not None:
            _validate_input(_ValidateArgument([dict], "additional_headers", additional_headers))
            self.__additional_headers = additional_headers
            for key, value in additional_headers.items():
                if value is None:
                    raise WeaviateInvalidInputError(
                        f"Value for key '{key}' in headers cannot be None."
                    )
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

        self._prepare_grpc_headers()

    def __add_weaviate_embedding_service_header(self, wcd_host: str) -> None:
        if not is_weaviate_domain(wcd_host):
            return

        self._headers["X-Weaviate-Cluster-URL"] = "https://" + wcd_host
        if isinstance(self._auth, AuthApiKey):
            # keeping for backwards compatibility for older clusters for now. On newer clusters, Embedding Service reuses Authorization header.
            self._headers["X-Weaviate-Api-Key"] = self._auth.api_key

    def set_integrations(self, integrations_config: List[_IntegrationConfig]) -> None:
        for integration in integrations_config:
            self._headers.update(integration._to_header())
            self.__additional_headers.update(integration._to_header())

    @overload
    def _make_client(self, colour: Literal["async"]) -> AsyncClient: ...

    @overload
    def _make_client(self, colour: Literal["sync"]) -> Client: ...

    def _make_client(self, colour: executor.Colour) -> Union[AsyncClient, Client]:
        if colour == "async":
            return AsyncClient(
                headers=self._headers,
                mounts=self._make_mounts(colour),
                trust_env=self.__trust_env,
            )
        if colour == "sync":
            return Client(
                headers=self._headers,
                mounts=self._make_mounts(colour),
                trust_env=self.__trust_env,
            )

    @overload
    def _make_mounts(self, colour: Literal["async"]) -> Dict[str, AsyncHTTPTransport]: ...

    @overload
    def _make_mounts(self, colour: Literal["sync"]) -> Dict[str, HTTPTransport]: ...

    def _make_mounts(
        self, colour: executor.Colour
    ) -> Union[Dict[str, AsyncHTTPTransport], Dict[str, HTTPTransport]]:
        if colour == "async":
            return {
                f"{key}://" if key == "http" or key == "https" else key: AsyncHTTPTransport(
                    limits=Limits(
                        max_connections=self.__connection_config.session_pool_maxsize,
                        max_keepalive_connections=self.__connection_config.session_pool_connections,
                    ),
                    proxy=Proxy(url=proxy),
                    retries=self.__connection_config.session_pool_max_retries,
                    trust_env=self.__trust_env,
                )
                for key, proxy in self._proxies.items()
                if key != "grpc"
            }
        if colour == "sync":
            return {
                f"{key}://" if key == "http" or key == "https" else key: HTTPTransport(
                    limits=Limits(
                        max_connections=self.__connection_config.session_pool_maxsize,
                        max_keepalive_connections=self.__connection_config.session_pool_connections,
                    ),
                    proxy=Proxy(url=proxy),
                    retries=self.__connection_config.session_pool_max_retries,
                    trust_env=self.__trust_env,
                )
                for key, proxy in self._proxies.items()
                if key != "grpc"
            }

    def is_connected(self) -> bool:
        return self._connected

    def get_current_bearer_token(self) -> str:
        if "authorization" in self._headers:
            return self._headers["authorization"]
        elif isinstance(self._client, (OAuth2Client, AsyncOAuth2Client)):
            return f"Bearer {self._client.token['access_token']}"
        return ""

    def _prepare_grpc_headers(self) -> None:
        self.__metadata_list: List[Tuple[str, str]] = []
        if len(self.additional_headers):
            for key, val in self.additional_headers.items():
                if val is not None:
                    self.__metadata_list.append((key.lower(), val))

        if self._auth is not None:
            if "X-Weaviate-Cluster-URL" in self._headers:
                self.__metadata_list.append(
                    ("x-weaviate-cluster-url", self._headers["X-Weaviate-Cluster-URL"])
                )

            if isinstance(self._auth, AuthApiKey):
                if "X-Weaviate-Api-Key" in self._headers:
                    # keeping for backwards compatibility for older clusters for now. On newer clusters, Embedding Service reuses Authorization header.
                    self.__metadata_list.append(
                        ("x-weaviate-api-key", self._headers["X-Weaviate-Api-Key"])
                    )
                self.__metadata_list.append(("authorization", "Bearer " + self._auth.api_key))
            else:
                self.__add_weaviate_embedding_service_auth_grpc_header()
                self.__metadata_list.append(
                    ("authorization", "dummy_will_be_refreshed_for_each_call")
                )

        if len(self.__metadata_list) > 0:
            self.__grpc_headers: Optional[Tuple[Tuple[str, str], ...]] = tuple(self.__metadata_list)
        else:
            self.__grpc_headers = None

    def __add_weaviate_embedding_service_auth_grpc_header(self) -> None:
        if is_weaviate_domain(self._connection_params.http.host):
            # keeping for backwards compatibility for older clusters for now. On newer clusters, Embedding Service reuses Authorization header.
            self.__metadata_list.append(
                ("x-weaviate-api-key", "dummy_will_be_refreshed_for_each_call")
            )

    def grpc_headers(self) -> Optional[Tuple[Tuple[str, str], ...]]:
        if self._auth is None or isinstance(self._auth, AuthApiKey):
            return self.__grpc_headers

        assert self.__grpc_headers is not None
        access_token = self.get_current_bearer_token()
        self.__refresh_weaviate_embedding_service_auth_grpc_header()
        # auth is last entry in list, rest is static
        self.__metadata_list[len(self.__metadata_list) - 1] = ("authorization", access_token)
        return tuple(self.__metadata_list)

    def __refresh_weaviate_embedding_service_auth_grpc_header(self) -> None:
        if is_weaviate_domain(self._connection_params.http.host):
            # keeping for backwards compatibility for older clusters for now. On newer clusters, Embedding Service reuses Authorization header.
            self.__metadata_list[len(self.__metadata_list) - 2] = (
                "x-weaviate-api-key",
                self.get_current_bearer_token(),
            )

    def _ping_grpc(self, colour: executor.Colour) -> Union[None, Awaitable[None]]:
        """Performs a grpc health check and raises WeaviateGRPCUnavailableError if not."""
        assert self._grpc_channel is not None
        try:
            res = self._grpc_channel.unary_unary(
                "/grpc.health.v1.Health/Check",
                request_serializer=health_pb2.HealthCheckRequest.SerializeToString,
                response_deserializer=health_pb2.HealthCheckResponse.FromString,
            )(health_pb2.HealthCheckRequest(), timeout=self.timeout_config.init)
            if colour == "async":

                async def execute() -> None:
                    assert isinstance(res, Awaitable)
                    try:
                        self.__handle_ping_response(cast(health_pb2.HealthCheckResponse, await res))
                    except Exception as e:
                        self.__handle_ping_exception(e)
                    return None

                return execute()
            assert not isinstance(res, Awaitable)
            return self.__handle_ping_response(cast(health_pb2.HealthCheckResponse, res))

        except Exception as e:
            self.__handle_ping_exception(e)
        return None

    def __handle_ping_response(self, res: health_pb2.HealthCheckResponse) -> None:
        if res.status != health_pb2.HealthCheckResponse.SERVING:
            raise WeaviateGRPCUnavailableError(
                f"v{self.server_version}", self._connection_params._grpc_address
            )
        return None

    def __handle_ping_exception(self, e: Exception) -> None:
        raise WeaviateGRPCUnavailableError(
            f"v{self.server_version}", self._connection_params._grpc_address
        ) from e

    @property
    def grpc_stub(self) -> Optional[weaviate_pb2_grpc.WeaviateStub]:
        if not self.is_connected():
            raise WeaviateClosedClientError()
        return self._grpc_stub

    def __del__(self) -> None:
        if self._client is not None or self._grpc_channel is not None:
            _Warnings.unclosed_connection()

    @property
    def server_version(self) -> str:
        """Version of the weaviate instance."""
        return str(self._weaviate_version)

    def get_proxies(self) -> Dict[str, str]:
        return self._proxies

    @property
    def additional_headers(self) -> Dict[str, str]:
        return self.__additional_headers

    def __make_clients(self, colour: Literal["async", "sync"]) -> None:
        self._client = self._make_client(colour)

    def open_connection_grpc(self, colour: executor.Colour) -> None:
        channel = self._connection_params._grpc_channel(
            proxies=self._proxies, grpc_msg_size=self._grpc_max_msg_size, is_async=colour == "async"
        )
        self._grpc_channel = channel
        assert self._grpc_channel is not None
        self._grpc_stub = weaviate_pb2_grpc.WeaviateStub(self._grpc_channel)

    def _open_connections_rest(
        self, auth_client_secret: Optional[AuthCredentials], colour: executor.Colour
    ) -> Union[None, Awaitable[None]]:
        # API keys are separate from OIDC and do not need any config from weaviate
        if auth_client_secret is not None and isinstance(auth_client_secret, AuthApiKey):
            self.__make_clients(colour)
            return executor.empty(colour)

        if "authorization" in self._headers and auth_client_secret is None:
            self.__make_clients(colour)
            return executor.empty(colour)

        # no need to check OIDC if no auth is provided and users dont want any checks at initialization time
        if self._skip_init_checks and auth_client_secret is None:
            self.__make_clients(colour)
            return executor.empty(colour)

        oidc_url = self.url + self._api_version_path + "/.well-known/openid-configuration"
        if colour == "async":

            async def get_oidc() -> None:
                async with self._make_client("async") as client:
                    try:
                        response = await client.get(oidc_url)
                    except Exception as e:
                        raise WeaviateConnectionError(
                            f"Error: {e}. \nIs Weaviate running and reachable at {self.url}?"
                        )
                res = self.__process_oidc_response(response, auth_client_secret, oidc_url, colour)
                if isinstance(res, Awaitable):
                    return await res
                else:
                    return res

            return get_oidc()

        with self._make_client("sync") as client:
            try:
                response = client.get(oidc_url)
            except Exception as e:
                raise WeaviateConnectionError(
                    f"Error: {e}. \nIs Weaviate running and reachable at {self.url}?"
                )
        res = self.__process_oidc_response(response, auth_client_secret, oidc_url, colour)
        assert not isinstance(res, Awaitable)
        return res

    def __process_oidc_response(
        self,
        response: Response,
        auth_client_secret: Optional[AuthCredentials],
        oidc_url: str,
        colour: executor.Colour,
    ) -> Union[None, Awaitable[None]]:
        if response.status_code == 200:
            # Some setups are behind proxies that return some default page - for example a login - for all requests.
            # If the response is not json, we assume that this is the case and try unauthenticated access. Any auth
            # header provided by the user is unaffected.
            try:
                resp = response.json()
            except Exception:
                _Warnings.auth_cannot_parse_oidc_config(oidc_url)
                self.__make_clients(colour)
                return executor.empty(colour)

            if auth_client_secret is not None:
                if colour == "async":

                    async def execute() -> None:
                        _auth = await executor.aresult(
                            _Auth.use(
                                oidc_config=resp,
                                credentials=auth_client_secret,
                                make_mounts=lambda: self._make_mounts("async"),
                                colour=colour,
                            )
                        )
                        try:
                            self._client = await _auth.aresult(_auth.get_auth_session())
                        except HTTPError as e:
                            raise AuthenticationFailedError(
                                f"Failed to authenticate with OIDC: {repr(e)}"
                            )

                        if isinstance(auth_client_secret, AuthClientCredentials):
                            # credentials should only be saved for client credentials, otherwise use refresh token
                            self._create_background_token_refresh(_auth)
                        else:
                            self._create_background_token_refresh()

                    return execute()
                else:
                    _auth = executor.result(
                        _Auth.use(
                            oidc_config=resp,
                            credentials=auth_client_secret,
                            make_mounts=lambda: self._make_mounts("sync"),
                            colour=colour,
                        )
                    )
                    try:
                        self._client = _auth.result(_auth.get_auth_session())
                    except HTTPError as e:
                        raise AuthenticationFailedError(
                            f"Failed to authenticate with OIDC: {repr(e)}"
                        )

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

                    You can instantiate the client with login credentials for Weaviate Cloud using

                    client = weaviate.connect_to_weaviate_cloud(
                      url=YOUR_WEAVIATE_URL,
                      auth_client_secret=wvc.init.Auth.api_key("YOUR_API_KEY")
                    )
                    """
                raise AuthenticationFailedError(msg)
        elif response.status_code == 404 and auth_client_secret is not None:
            _Warnings.auth_with_anon_weaviate()
            self.__make_clients(colour)
        else:
            self.__make_clients(colour)
        return executor.empty(colour)

    def _create_background_token_refresh(self, _auth: Optional[_Auth] = None) -> None:
        """Create a background thread that periodically refreshes access and refresh tokens.

        While the underlying library refreshes tokens, it does not have an internal cronjob that checks every
        X-seconds if a token has expired. If there is no activity for longer than the refresh tokens lifetime, it will
        expire. Therefore, refresh manually shortly before expiration time is up.
        """
        assert isinstance(self._client, (OAuth2Client, AsyncOAuth2Client))
        if "refresh_token" not in self._client.token and _auth is None:
            return

        # make an event loop sidecar thread for running async token refreshing
        event_loop = (
            _EventLoopSingleton.get_instance()
            if isinstance(self._client, AsyncOAuth2Client)
            else None
        )

        expires_in: int = self._client.token.get(
            "expires_in", 60
        )  # use 1minute as token lifetime if not supplied
        self._shutdown_background_event = Event()

        def refresh_token() -> None:
            if isinstance(self._client, AsyncOAuth2Client):
                assert event_loop is not None
                self._client.token = event_loop.run_until_complete(
                    self._client.refresh_token, url=self._client.metadata["token_endpoint"]
                )
            elif isinstance(self._client, OAuth2Client):
                self._client.token = self._client.refresh_token(
                    url=self._client.metadata["token_endpoint"]
                )

        def refresh_session() -> None:
            assert _auth is not None
            if isinstance(self._client, AsyncOAuth2Client):
                assert event_loop is not None
                new_session = event_loop.run_until_complete(
                    _auth.aresult, result=_auth.get_auth_session()
                )
                self._client.token = event_loop.run_until_complete(new_session.fetch_token)
            elif isinstance(self._client, OAuth2Client):
                new_session = _auth.result(_auth.get_auth_session())
                self._client.token = new_session.fetch_token()

        def update_refresh_time() -> int:
            assert isinstance(self._client, (OAuth2Client, AsyncOAuth2Client))
            return self._client.token.get("expires_in", 60) - 30

        def periodic_refresh_token(refresh_time: int, _auth: Optional[_Auth]) -> None:
            while (
                self._shutdown_background_event is not None
                and not self._shutdown_background_event.is_set()
            ):
                # use refresh token when available
                time.sleep(max(refresh_time, 1))
                try:
                    if self._client is None:
                        continue
                    elif (
                        isinstance(self._client, (OAuth2Client, AsyncOAuth2Client))
                        and "refresh_token" in self._client.token
                    ):
                        refresh_token()
                    else:
                        # client credentials usually does not contain a refresh token => get a new token using the
                        # saved credentials
                        refresh_session()
                    refresh_time = update_refresh_time()
                except HTTPError as exc:
                    # retry again after one second, might be an unstable connection
                    refresh_time = 1
                    _Warnings.token_refresh_failed(exc)

        demon = Thread(
            target=periodic_refresh_token,
            args=(expires_in, _auth),
            daemon=True,
            name="TokenRefresh",
        )
        demon.start()

    def __get_latest_headers(self) -> Dict[str, str]:
        if "authorization" in self._headers:
            return self._headers

        auth_token = self.get_current_bearer_token()
        if auth_token == "":
            return self._headers

        # bearer token can change over time (OIDC) so we need to get the current one for each request
        copied_headers = copy(self._headers)
        copied_headers.update({"authorization": self.get_current_bearer_token()})
        self.__refresh_weaviate_embedding_service_auth_header(copied_headers)
        return copied_headers

    def __refresh_weaviate_embedding_service_auth_header(self, headers: dict[str, str]) -> None:
        if is_weaviate_domain(self._connection_params.http.host):
            # keeping for backwards compatibility for older clusters for now. On newer clusters, Embedding Service reuses Authorization header.
            headers.update({"x-weaviate-api-key": self.get_current_bearer_token()})

    def __get_timeout(
        self, method: Literal["DELETE", "GET", "HEAD", "PATCH", "POST", "PUT"], is_gql_query: bool
    ) -> Timeout:
        """Get the timeout for the request.

        In this way, the client waits the `httpx` default of 5s when connecting to a socket (connect), writing chunks (write), and
        acquiring a connection from the pool (pool), but a custom amount as specified for reading the response (read).

        From the PoV of the user, a request is considered to be timed out if no response is received within the specified time.
        They specify the times depending on how they expect Weaviate to behave. For example, a query might take longer than an insert or vice versa
        but, in either case, the user only cares about how long it takes for a response to be received.

        https://www.python-httpx.org/advanced/timeouts/
        """
        timeout = None
        if method == "DELETE" or method == "PATCH" or method == "PUT":
            timeout = self.timeout_config.insert
        elif method == "GET" or method == "HEAD":
            timeout = self.timeout_config.query
        elif method == "POST" and is_gql_query:
            timeout = self.timeout_config.query
        elif method == "POST" and not is_gql_query:
            timeout = self.timeout_config.insert
        return Timeout(
            timeout=5.0, read=timeout, pool=self.__connection_config.session_pool_timeout
        )

    def __handle_exceptions(self, e: Exception, error_msg: str) -> None:
        if isinstance(e, RuntimeError):
            raise WeaviateClosedClientError() from e
        if isinstance(e, ConnectError):
            raise WeaviateConnectionError(error_msg) from e
        if isinstance(e, ReadTimeout):
            raise WeaviateTimeoutError(error_msg) from e
        raise e

    def __handle_response(
        self, response: Response, error_msg: str, status_codes: Optional[_ExpectedStatusCodes]
    ) -> Response:
        if response.status_code == 403:
            raise InsufficientPermissionsError(response)
        if status_codes is not None and response.status_code not in status_codes.ok:
            raise UnexpectedStatusCodeError(error_msg, response)
        return response

    def _send(
        self,
        method: Literal["DELETE", "GET", "HEAD", "PATCH", "POST", "PUT"],
        *,
        url: str,
        error_msg: str,
        status_codes: Optional[_ExpectedStatusCodes],
        is_gql_query: bool = False,
        weaviate_object: Optional[JSONPayload] = None,
        params: Optional[Dict[str, Any]] = None,
        check_is_connected: bool = True,
    ) -> executor.Result[Response]:
        if check_is_connected and not self.is_connected():
            raise WeaviateClosedClientError()
        if self.embedded_db is not None:
            self.embedded_db.ensure_running()
        assert self._client is not None
        request = self._client.build_request(
            method,
            url,
            json=weaviate_object,
            params=params,
            headers=self.__get_latest_headers(),
            timeout=self.__get_timeout(method, is_gql_query),
        )

        def resp(res: Response) -> Response:
            return self.__handle_response(res, error_msg, status_codes)

        def exc(e: Exception) -> None:
            self.__handle_exceptions(e, error_msg)

        return executor.execute(
            response_callback=resp,
            exception_callback=exc,
            method=self._client.send,
            request=request,
        )

    def close(self, colour: executor.Colour) -> executor.Result[None]:
        if self.embedded_db is not None:
            self.embedded_db.stop()
        if colour == "async":

            async def execute() -> None:
                if self._client is not None:
                    assert isinstance(self._client, AsyncClient)
                    await self._client.aclose()
                    self._client = None
                if self._grpc_stub is not None:
                    assert self._grpc_channel is not None
                    assert isinstance(self._grpc_channel, AsyncChannel)
                    await self._grpc_channel.close()
                    self._grpc_stub = None
                    self._grpc_channel = None
                self._connected = False

            return execute()
        if self._client is not None:
            assert isinstance(self._client, Client)
            self._client.close()
            self._client = None
        if self._grpc_stub is not None:
            assert self._grpc_channel is not None
            assert isinstance(self._grpc_channel, SyncChannel)
            self._grpc_channel.close()
            self._grpc_stub = None
            self._grpc_channel = None
        self._connected = False

    def _check_package_version(self, colour: executor.Colour) -> executor.Result[None]:
        def resp(res: Response) -> None:
            pkg_info: dict = res.json().get("info", {})
            latest_version = pkg_info.get("version", "unknown version")
            if is_weaviate_client_too_old(client_version, latest_version):
                _Warnings.weaviate_client_too_old_vs_latest(client_version, latest_version)

        try:
            if colour == "async":

                async def _execute() -> None:
                    async with AsyncClient() as client:
                        res = await client.get(PYPI_PACKAGE_URL, timeout=self.timeout_config.init)
                    return resp(res)

                return _execute()
            with Client() as client:
                res = client.get(PYPI_PACKAGE_URL, timeout=self.timeout_config.init)
            return resp(res)
        except RequestError:
            pass  # ignore any errors related to requests, it is a best-effort warning

    def supports_groupby_in_bm25_and_hybrid(self) -> bool:
        return self._weaviate_version.is_at_least(1, 25, 0)

    def delete(
        self,
        path: str,
        weaviate_object: Optional[JSONPayload] = None,
        params: Optional[Dict[str, Any]] = None,
        error_msg: str = "",
        status_codes: Optional[_ExpectedStatusCodes] = None,
    ) -> executor.Result[Response]:
        return self._send(
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
    ) -> executor.Result[Response]:
        return self._send(
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
        is_gql_query: bool = False,
    ) -> executor.Result[Response]:
        return self._send(
            "POST",
            url=self.url + self._api_version_path + path,
            weaviate_object=weaviate_object,
            params=params,
            error_msg=error_msg,
            status_codes=status_codes,
            is_gql_query=is_gql_query,
        )

    def put(
        self,
        path: str,
        weaviate_object: JSONPayload,
        params: Optional[Dict[str, Any]] = None,
        error_msg: str = "",
        status_codes: Optional[_ExpectedStatusCodes] = None,
    ) -> executor.Result[Response]:
        return self._send(
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
        check_is_connected: bool = True,
    ) -> executor.Result[Response]:
        return self._send(
            "GET",
            url=self.url + self._api_version_path + path,
            params=params,
            error_msg=error_msg,
            status_codes=status_codes,
            check_is_connected=check_is_connected,
        )

    def head(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        error_msg: str = "",
        status_codes: Optional[_ExpectedStatusCodes] = None,
    ) -> executor.Result[Response]:
        return self._send(
            "HEAD",
            url=self.url + self._api_version_path + path,
            params=params,
            error_msg=error_msg,
            status_codes=status_codes,
        )

    def get_meta(self, check_is_connected: bool = True) -> executor.Result[Dict[str, str]]:
        def resp(res: Response) -> Dict[str, str]:
            data = _decode_json_response_dict(res, "Meta endpoint")
            assert data is not None
            return data

        return executor.execute(
            response_callback=resp,
            method=self.get,
            path="/meta",
            check_is_connected=check_is_connected,
        )

    def get_open_id_configuration(self) -> executor.Result[Optional[Dict[str, Any]]]:
        def resp(res: Response) -> Optional[Dict[str, Any]]:
            if res.status_code == 200:
                return _decode_json_response_dict(res, "OpenID Configuration")
            if res.status_code == 404:
                return None
            raise UnexpectedStatusCodeError("Meta endpoint", res)

        return executor.execute(
            response_callback=resp, method=self.get, path="/.well-known/openid-configuration"
        )


class ConnectionSync(_ConnectionBase):
    """Connection class used to communicate to a weaviate instance."""

    def connect(self) -> None:
        if self._connected:
            return None

        self._open_connections_rest(self._auth, "sync")

        # need this to get the version of weaviate for version checks and proper GRPC configuration
        try:
            meta = executor.result(self.get_meta(False))
            self._weaviate_version = _ServerVersion.from_string(meta["version"])
            if "grpcMaxMessageSize" in meta:
                self._grpc_max_msg_size = int(meta["grpcMaxMessageSize"])
            # Add warning later, when weaviate supported it for a while
            # else:
            #     _Warnings.grpc_max_msg_size_not_found()
        except (
            WeaviateConnectionError,
            ReadError,
            RemoteProtocolError,
            SSLZeroReturnError,  # required for async 3.8,3.9 due to ssl.SSLZeroReturnError: TLS/SSL connection has been closed (EOF) (_ssl.c:1131)
        ) as e:
            self._connected = False
            raise WeaviateStartUpError(f"Could not connect to Weaviate:{e}.") from e

        self.open_connection_grpc("sync")
        if self.embedded_db is not None:
            try:
                self.wait_for_weaviate(10)
            except WeaviateStartUpError as e:
                self.embedded_db.stop()
                self._connected = False
                raise e

        # do it after all other init checks so as not to break all the tests
        if self._weaviate_version.is_lower_than(1, 23, 7):
            self._connected = False
            raise WeaviateStartUpError(
                f"Weaviate version {self._weaviate_version} is not supported. Please use Weaviate version 1.23.7 or higher."
            )

        if not self._skip_init_checks:
            try:
                executor.result(self._ping_grpc("sync"))
                executor.result(self._check_package_version("sync"))
            except Exception as e:
                self._connected = False
                raise e

        self._connected = True

    def wait_for_weaviate(self, startup_period: int) -> None:
        for _i in range(startup_period):
            try:
                executor.result(
                    self.get("/.well-known/ready", check_is_connected=False)
                ).raise_for_status()
                return
            except (ConnectError, ReadError, TimeoutError, HTTPStatusError):
                time.sleep(1)

        try:
            executor.result(
                self.get("/.well-known/ready", check_is_connected=False)
            ).raise_for_status()
            return
        except (ConnectError, ReadError, TimeoutError, HTTPStatusError) as error:
            raise WeaviateStartUpError(
                f"Weaviate did not start up in {startup_period} seconds. Either the Weaviate URL {self.url} is wrong or Weaviate did not start up in the interval given in 'startup_period'."
            ) from error

    def grpc_search(self, request: search_get_pb2.SearchRequest) -> search_get_pb2.SearchReply:
        try:
            assert self.grpc_stub is not None
            res = _Retry(4).with_exponential_backoff(
                0,
                f"Searching in collection {request.collection}",
                self.grpc_stub.Search,
                request,
                metadata=self.grpc_headers(),
                timeout=self.timeout_config.query,
            )
            return cast(search_get_pb2.SearchReply, res)
        except RpcError as e:
            error = cast(Call, e)
            if error.code() == StatusCode.PERMISSION_DENIED:
                raise InsufficientPermissionsError(error)
            raise WeaviateQueryError(str(error.details()), "GRPC search")  # pyright: ignore
        except WeaviateRetryError as e:
            raise WeaviateQueryError(str(e), "GRPC search")  # pyright: ignore

    def grpc_batch_objects(
        self, request: batch_pb2.BatchObjectsRequest, timeout: Union[int, float], max_retries: float
    ) -> Dict[int, str]:
        try:
            assert self.grpc_stub is not None
            res = _Retry(max_retries).with_exponential_backoff(
                count=0,
                error="Batch objects",
                f=self.grpc_stub.BatchObjects,
                request=request,
                metadata=self.grpc_headers(),
                timeout=timeout,
            )
            res = cast(batch_pb2.BatchObjectsReply, res)

            objects: Dict[int, str] = {}
            for err in res.errors:
                objects[err.index] = err.error
            return objects
        except RpcError as e:
            error = cast(Call, e)
            if error.code() == StatusCode.PERMISSION_DENIED:
                raise InsufficientPermissionsError(error)
            raise WeaviateBatchError(str(error.details()))

    def grpc_batch_delete(
        self, request: batch_delete_pb2.BatchDeleteRequest
    ) -> batch_delete_pb2.BatchDeleteReply:
        try:
            assert self.grpc_stub is not None
            return cast(
                batch_delete_pb2.BatchDeleteReply,
                self.grpc_stub.BatchDelete(
                    request,
                    metadata=self.grpc_headers(),
                    timeout=self.timeout_config.insert,
                ),
            )
        except RpcError as e:
            error = cast(Call, e)
            if error.code() == StatusCode.PERMISSION_DENIED:
                raise InsufficientPermissionsError(error)
            raise WeaviateDeleteManyError(str(error.details()))

    def grpc_tenants_get(
        self, request: tenants_pb2.TenantsGetRequest
    ) -> tenants_pb2.TenantsGetReply:
        try:
            assert self.grpc_stub is not None
            res = _Retry().with_exponential_backoff(
                0,
                f"Get tenants for collection {request.collection}",
                self.grpc_stub.TenantsGet,
                request,
                metadata=self.grpc_headers(),
                timeout=self.timeout_config.query,
            )
        except RpcError as e:
            error = cast(Call, e)
            if error.code() == StatusCode.PERMISSION_DENIED:
                raise InsufficientPermissionsError(error)
            raise WeaviateTenantGetError(str(error.details())) from e

        return cast(tenants_pb2.TenantsGetReply, res)

    def grpc_aggregate(
        self, request: aggregate_pb2.AggregateRequest
    ) -> aggregate_pb2.AggregateReply:
        try:
            assert self.grpc_stub is not None
            res = _Retry(4).with_exponential_backoff(
                0,
                f"Searching in collection {request.collection}",
                self.grpc_stub.Aggregate,
                request,
                metadata=self.grpc_headers(),
                timeout=self.timeout_config.query,
            )
            return cast(aggregate_pb2.AggregateReply, res)
        except RpcError as e:
            error = cast(Call, e)
            if error.code() == StatusCode.PERMISSION_DENIED:
                raise InsufficientPermissionsError(error)
            raise WeaviateQueryError(str(e), "GRPC search")  # pyright: ignore
        except WeaviateRetryError as e:
            raise WeaviateQueryError(str(e), "GRPC search")  # pyright: ignore


class ConnectionAsync(_ConnectionBase):
    """Connection class used to communicate to a weaviate instance."""

    async def connect(self) -> None:
        if self._connected:
            return None

        await executor.aresult(self._open_connections_rest(self._auth, "async"))

        # need this to get the version of weaviate for version checks and proper GRPC configuration
        try:
            meta = await self.get_meta(False)
            self._weaviate_version = _ServerVersion.from_string(meta["version"])
            if "grpcMaxMessageSize" in meta:
                self._grpc_max_msg_size = int(meta["grpcMaxMessageSize"])
            # Add warning later, when weaviate supported it for a while
            # else:
            #     _Warnings.grpc_max_msg_size_not_found()
        except (
            WeaviateConnectionError,
            ReadError,
            RemoteProtocolError,
            SSLZeroReturnError,  # required for async 3.8,3.9 due to ssl.SSLZeroReturnError: TLS/SSL connection has been closed (EOF) (_ssl.c:1131)
        ) as e:
            self._connected = False
            raise WeaviateStartUpError(f"Could not connect to Weaviate:{e}.") from e

        self.open_connection_grpc("async")
        if self.embedded_db is not None:
            try:
                await self.wait_for_weaviate(10)
            except WeaviateStartUpError as e:
                self.embedded_db.stop()
                self._connected = False
                raise e

        # do it after all other init checks so as not to break all the tests
        if self._weaviate_version.is_lower_than(1, 23, 7):
            self._connected = False
            raise WeaviateStartUpError(
                f"Weaviate version {self._weaviate_version} is not supported. Please use Weaviate version 1.23.7 or higher."
            )

        if not self._skip_init_checks:
            try:
                await executor.aresult(self._ping_grpc("async"))
                await executor.aresult(self._check_package_version("async"))
            except Exception as e:
                self._connected = False
                raise e

        self._connected = True

    async def wait_for_weaviate(self, startup_period: int) -> None:
        for _i in range(startup_period):
            try:
                (
                    await executor.aresult(self.get("/.well-known/ready", check_is_connected=False))
                ).raise_for_status()
                return
            except (ConnectError, ReadError, TimeoutError, HTTPStatusError):
                time.sleep(1)

        try:
            (
                await executor.aresult(self.get("/.well-known/ready", check_is_connected=False))
            ).raise_for_status()
            return
        except (ConnectError, ReadError, TimeoutError, HTTPStatusError) as error:
            raise WeaviateStartUpError(
                f"Weaviate did not start up in {startup_period} seconds. Either the Weaviate URL {self.url} is wrong or Weaviate did not start up in the interval given in 'startup_period'."
            ) from error

    async def grpc_search(
        self, request: search_get_pb2.SearchRequest
    ) -> search_get_pb2.SearchReply:
        try:
            assert self.grpc_stub is not None
            res = await _Retry(4).awith_exponential_backoff(
                0,
                f"Searching in collection {request.collection}",
                self.grpc_stub.Search,
                request,
                metadata=self.grpc_headers(),
                timeout=self.timeout_config.query,
            )
            return cast(search_get_pb2.SearchReply, res)
        except AioRpcError as e:
            if e.code().name == PERMISSION_DENIED:
                raise InsufficientPermissionsError(e)
            raise WeaviateQueryError(str(e), "GRPC search")  # pyright: ignore
        except WeaviateRetryError as e:
            raise WeaviateQueryError(str(e), "GRPC search")  # pyright: ignore

    async def grpc_batch_objects(
        self, request: batch_pb2.BatchObjectsRequest, timeout: Union[int, float], max_retries: float
    ) -> Dict[int, str]:
        try:
            assert self.grpc_stub is not None
            res = await _Retry(max_retries).awith_exponential_backoff(
                count=0,
                error="Batch objects",
                f=self.grpc_stub.BatchObjects,
                request=request,
                metadata=self.grpc_headers(),
                timeout=timeout,
            )
            res = cast(batch_pb2.BatchObjectsReply, res)

            objects: Dict[int, str] = {}
            for err in res.errors:
                objects[err.index] = err.error
            return objects
        except AioRpcError as e:
            if e.code().name == PERMISSION_DENIED:
                raise InsufficientPermissionsError(e)
            raise WeaviateBatchError(str(e)) from e

    async def grpc_batch_delete(
        self, request: batch_delete_pb2.BatchDeleteRequest
    ) -> batch_delete_pb2.BatchDeleteReply:
        try:
            assert self.grpc_stub is not None
            return await self.grpc_stub.BatchDelete(
                request,
                metadata=self.grpc_headers(),
                timeout=self.timeout_config.insert,
            )
        except AioRpcError as e:
            if e.code().name == PERMISSION_DENIED:
                raise InsufficientPermissionsError(e)
            raise WeaviateDeleteManyError(str(e))

    async def grpc_tenants_get(
        self, request: tenants_pb2.TenantsGetRequest
    ) -> tenants_pb2.TenantsGetReply:
        try:
            assert self.grpc_stub is not None
            res = await _Retry().awith_exponential_backoff(
                0,
                f"Get tenants for collection {request.collection}",
                self.grpc_stub.TenantsGet,
                request,
                metadata=self.grpc_headers(),
                timeout=self.timeout_config.query,
            )
        except AioRpcError as e:
            if e.code().name == PERMISSION_DENIED:
                raise InsufficientPermissionsError(e)
            raise WeaviateTenantGetError(str(e)) from e

        return cast(tenants_pb2.TenantsGetReply, res)

    async def grpc_aggregate(
        self, request: aggregate_pb2.AggregateRequest
    ) -> aggregate_pb2.AggregateReply:
        try:
            assert self.grpc_stub is not None
            res = await _Retry(4).awith_exponential_backoff(
                0,
                f"Searching in collection {request.collection}",
                self.grpc_stub.Aggregate,
                request,
                metadata=self.grpc_headers(),
                timeout=self.timeout_config.query,
            )
            return cast(aggregate_pb2.AggregateReply, res)
        except AioRpcError as e:
            if e.code().name == PERMISSION_DENIED:
                raise InsufficientPermissionsError(e)
            raise WeaviateQueryError(str(e), "GRPC search")  # pyright: ignore
        except WeaviateRetryError as e:
            raise WeaviateQueryError(str(e), "GRPC search")  # pyright: ignore


ConnectionV4 = ConnectionAsync
Connection = Union[ConnectionSync, ConnectionAsync]
ConnectionType = TypeVar("ConnectionType", ConnectionSync, ConnectionAsync)
