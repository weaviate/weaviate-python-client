from __future__ import annotations

import asyncio
import time
from copy import copy
from dataclasses import dataclass, field
from ssl import SSLZeroReturnError
from threading import Event, Thread
from typing import Any, Dict, List, Literal, Optional, Tuple, Union, cast

from authlib.integrations.httpx_client import (  # type: ignore
    AsyncOAuth2Client,
    OAuth2Client,
)
from grpc.aio import Channel  # type: ignore
from grpc_health.v1 import health_pb2  # type: ignore

# from grpclib.client import Channel
from httpx import (
    AsyncClient,
    AsyncHTTPTransport,
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
from weaviate.auth import (
    AuthCredentials,
    AuthApiKey,
    AuthClientCredentials,
)
from weaviate.config import ConnectionConfig, Proxies, Timeout as TimeoutConfig
from weaviate.connect.authentication_async import _Auth
from weaviate.connect.base import (
    ConnectionParams,
    JSONPayload,
    _get_proxies,
)
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
)
from weaviate.proto.v1 import weaviate_pb2_grpc
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


class ConnectionV4:
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
        loop: asyncio.AbstractEventLoop,  # required for background token refresh
        embedded_db: Optional[EmbeddedV4] = None,
    ):
        self.url = connection_params._http_url
        self.embedded_db = embedded_db
        self._api_version_path = "/v1"
        self._client: Optional[AsyncSession] = None
        self.__additional_headers = {}
        self._auth = auth_client_secret
        self._connection_params = connection_params
        self._grpc_stub: Optional[weaviate_pb2_grpc.WeaviateStub] = None
        self._grpc_channel: Optional[Channel] = None
        self.timeout_config = timeout_config
        self.__connection_config = connection_config
        self.__trust_env = trust_env
        self._weaviate_version = _ServerVersion.from_string("")
        self._grpc_max_msg_size: Optional[int] = None
        self.__connected = False
        self.__loop = loop

        self._headers = {"content-type": "application/json"}
        self.__add_weaviate_embedding_service_header(connection_params.http.host)
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

        self._prepare_grpc_headers()

    def __add_weaviate_embedding_service_header(self, wcd_host: str) -> None:
        if not is_weaviate_domain(wcd_host) or not isinstance(self._auth, AuthApiKey):
            return
        self._headers["X-Weaviate-Api-Key"] = self._auth.api_key
        self._headers["X-Weaviate-Cluster-URL"] = "https://" + wcd_host

    async def connect(self, skip_init_checks: bool) -> None:
        self.__connected = True

        await self._open_connections_rest(self._auth, skip_init_checks)

        # need this to get the version of weaviate for version checks and proper GRPC configuration
        try:
            meta = await self.get_meta()
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
            self.__connected = False
            raise WeaviateStartUpError(f"Could not connect to Weaviate:{e}.") from e

        await self.open_connection_grpc()
        self.__connected = True
        if self.embedded_db is not None:
            try:
                await self.wait_for_weaviate(10)
            except WeaviateStartUpError as e:
                self.embedded_db.stop()
                self.__connected = False
                raise e

        # do it after all other init checks so as not to break all the tests
        if self._weaviate_version.is_lower_than(1, 23, 7):
            self.__connected = False
            raise WeaviateStartUpError(
                f"Weaviate version {self._weaviate_version} is not supported. Please use Weaviate version 1.23.7 or higher."
            )

        if not skip_init_checks:
            try:
                await asyncio.gather(self._ping_grpc(), self.__check_package_version())
            except Exception as e:
                self.__connected = False
                raise e

        self.__connected = True

    async def __check_package_version(self) -> None:
        try:
            async with AsyncClient() as client:
                res = await client.get(PYPI_PACKAGE_URL, timeout=self.timeout_config.init)
            pkg_info: dict = res.json().get("info", {})
            latest_version = pkg_info.get("version", "unknown version")
            if is_weaviate_client_too_old(client_version, latest_version):
                _Warnings.weaviate_client_too_old_vs_latest(client_version, latest_version)
        except RequestError:
            pass  # ignore any errors related to requests, it is a best-effort warning

    def is_connected(self) -> bool:
        return self.__connected

    def set_integrations(self, integrations_config: List[_IntegrationConfig]) -> None:
        for integration in integrations_config:
            self._headers.update(integration._to_header())
            self.__additional_headers.update(integration._to_header())

    def _make_mounts(self) -> Dict[str, AsyncHTTPTransport]:
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

    def __make_async_client(self) -> AsyncClient:
        return AsyncClient(
            headers=self._headers,
            mounts=self._make_mounts(),
            trust_env=self.__trust_env,
        )

    def __make_clients(self) -> None:
        self._client = self.__make_async_client()

    async def _open_connections_rest(
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
        async with self.__make_async_client() as client:
            try:
                response = await client.get(oidc_url)
            except Exception as e:
                raise WeaviateConnectionError(
                    f"Error: {e}. \nIs Weaviate running and reachable at {self.url}?"
                )

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
                _auth = await _Auth.use(
                    oidc_config=resp,
                    credentials=auth_client_secret,
                    connection=self,
                )
                try:
                    self._client = await _auth.get_auth_session()
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

                    You can instantiate the client with login credentials for Weaviate Cloud using

                    client = weaviate.connect_to_weaviate_cloud(
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

    async def open_connection_grpc(self) -> None:
        self._grpc_channel = self._connection_params._grpc_channel(
            proxies=self._proxies,
            grpc_msg_size=self._grpc_max_msg_size,
        )
        assert self._grpc_channel is not None
        self._grpc_stub = weaviate_pb2_grpc.WeaviateStub(self._grpc_channel)

    def get_current_bearer_token(self) -> str:
        if not self.is_connected():
            raise WeaviateClosedClientError()

        if "authorization" in self._headers:
            return self._headers["authorization"]
        elif isinstance(self._client, AsyncOAuth2Client):
            return f"Bearer {self._client.token['access_token']}"
        return ""

    def _create_background_token_refresh(self, _auth: Optional[_Auth] = None) -> None:
        """Create a background thread that periodically refreshes access and refresh tokens.

        While the underlying library refreshes tokens, it does not have an internal cronjob that checks every
        X-seconds if a token has expired. If there is no activity for longer than the refresh tokens lifetime, it will
        expire. Therefore, refresh manually shortly before expiration time is up."""
        assert isinstance(self._client, AsyncOAuth2Client)
        if "refresh_token" not in self._client.token and _auth is None:
            return

        expires_in: int = self._client.token.get(
            "expires_in", 60
        )  # use 1minute as token lifetime if not supplied
        self._shutdown_background_event = Event()

        def periodic_refresh_token(refresh_time: int, _auth: Optional[_Auth]) -> None:
            time.sleep(max(refresh_time - 30, 1))
            while (
                self._shutdown_background_event is not None
                and not self._shutdown_background_event.is_set()
            ):
                # use refresh token when available
                try:
                    if "refresh_token" in cast(AsyncOAuth2Client, self._client).token:
                        assert isinstance(self._client, AsyncOAuth2Client)
                        self._client.token = asyncio.run_coroutine_threadsafe(
                            self._client.refresh_token(
                                self._client.metadata["token_endpoint"]
                            ),  # pyright: ignore # due to AsyncOAuth2Client not providing correct type
                            self.__loop,
                        ).result()
                        expires_in = self._client.token.get("expires_in", 60)
                        assert isinstance(expires_in, int)
                        refresh_time = expires_in - 30
                    else:
                        # client credentials usually does not contain a refresh token => get a new token using the
                        # saved credentials
                        assert _auth is not None
                        assert isinstance(self._client, AsyncOAuth2Client)
                        new_session = asyncio.run_coroutine_threadsafe(
                            _auth.get_auth_session(), self.__loop
                        ).result()
                        self._client.token = asyncio.run_coroutine_threadsafe(
                            new_session.fetch_token(),  # pyright: ignore # due to AsyncOAuth2Client not providing correct type
                            self.__loop,
                        ).result()
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

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        if self._grpc_stub is not None:
            assert self._grpc_channel is not None
            await self._grpc_channel.close()
            self._grpc_stub = None
            self._grpc_channel = None
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

    def __get_timeout(
        self, method: Literal["DELETE", "GET", "HEAD", "PATCH", "POST", "PUT"], is_gql_query: bool
    ) -> Timeout:
        """
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

    async def __send(
        self,
        method: Literal["DELETE", "GET", "HEAD", "PATCH", "POST", "PUT"],
        url: str,
        error_msg: str,
        status_codes: Optional[_ExpectedStatusCodes],
        is_gql_query: bool = False,
        weaviate_object: Optional[JSONPayload] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Response:
        if not self.is_connected():
            raise WeaviateClosedClientError()
        if self.embedded_db is not None:
            self.embedded_db.ensure_running()
        assert self._client is not None
        try:
            req = self._client.build_request(
                method,
                url,
                json=weaviate_object,
                params=params,
                headers=self.__get_latest_headers(),
                timeout=self.__get_timeout(method, is_gql_query),
            )
            res = await self._client.send(req)
            if res.status_code == 403:
                raise InsufficientPermissionsError(res)
            if status_codes is not None and res.status_code not in status_codes.ok:
                raise UnexpectedStatusCodeError(error_msg, response=res)
            return cast(Response, res)
        except RuntimeError as e:
            raise WeaviateClosedClientError() from e
        except ConnectError as conn_err:
            raise WeaviateConnectionError(error_msg) from conn_err
        except ReadTimeout as read_err:
            raise WeaviateTimeoutError(error_msg) from read_err
        except Exception as e:
            raise e

    async def delete(
        self,
        path: str,
        weaviate_object: Optional[JSONPayload] = None,
        params: Optional[Dict[str, Any]] = None,
        error_msg: str = "",
        status_codes: Optional[_ExpectedStatusCodes] = None,
    ) -> Response:
        return await self.__send(
            "DELETE",
            url=self.url + self._api_version_path + path,
            weaviate_object=weaviate_object,
            params=params,
            error_msg=error_msg,
            status_codes=status_codes,
        )

    async def patch(
        self,
        path: str,
        weaviate_object: JSONPayload,
        params: Optional[Dict[str, Any]] = None,
        error_msg: str = "",
        status_codes: Optional[_ExpectedStatusCodes] = None,
    ) -> Response:
        return await self.__send(
            "PATCH",
            url=self.url + self._api_version_path + path,
            weaviate_object=weaviate_object,
            params=params,
            error_msg=error_msg,
            status_codes=status_codes,
        )

    async def post(
        self,
        path: str,
        weaviate_object: JSONPayload,
        params: Optional[Dict[str, Any]] = None,
        error_msg: str = "",
        status_codes: Optional[_ExpectedStatusCodes] = None,
        is_gql_query: bool = False,
    ) -> Response:
        return await self.__send(
            "POST",
            url=self.url + self._api_version_path + path,
            weaviate_object=weaviate_object,
            params=params,
            error_msg=error_msg,
            status_codes=status_codes,
            is_gql_query=is_gql_query,
        )

    async def put(
        self,
        path: str,
        weaviate_object: JSONPayload,
        params: Optional[Dict[str, Any]] = None,
        error_msg: str = "",
        status_codes: Optional[_ExpectedStatusCodes] = None,
    ) -> Response:
        return await self.__send(
            "PUT",
            url=self.url + self._api_version_path + path,
            weaviate_object=weaviate_object,
            params=params,
            error_msg=error_msg,
            status_codes=status_codes,
        )

    async def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        error_msg: str = "",
        status_codes: Optional[_ExpectedStatusCodes] = None,
    ) -> Response:
        return await self.__send(
            "GET",
            url=self.url + self._api_version_path + path,
            params=params,
            error_msg=error_msg,
            status_codes=status_codes,
        )

    async def head(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        error_msg: str = "",
        status_codes: Optional[_ExpectedStatusCodes] = None,
    ) -> Response:
        return await self.__send(
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

    def get_proxies(self) -> Dict[str, str]:
        return self._proxies

    @property
    def additional_headers(self) -> Dict[str, str]:
        return self.__additional_headers

    async def get_meta(self) -> Dict[str, str]:
        """
        Returns the meta endpoint.
        """
        response = await self.get(path="/meta")
        res = _decode_json_response_dict(response, "Meta endpoint")
        assert res is not None
        return res

    async def get_open_id_configuration(self) -> Optional[Dict[str, Any]]:
        """
        Get the openid-configuration.
        """

        response = await self.get(path="/.well-known/openid-configuration")
        if response.status_code == 200:
            return _decode_json_response_dict(response, "OpenID Configuration")
        if response.status_code == 404:
            return None
        raise UnexpectedStatusCodeError("Meta endpoint", response)

    def supports_groupby_in_bm25_and_hybrid(self) -> bool:
        return self._weaviate_version.is_at_least(1, 25, 0)

    async def wait_for_weaviate(self, startup_period: int) -> None:
        """
        Waits until weaviate is ready or the time limit given in 'startup_period' has passed.

        Parameters
        ----------
        startup_period : int
            Describes how long the client will wait for weaviate to start in seconds.

        Raises
        ------
        WeaviateStartUpError
            If weaviate takes longer than the time limit to respond.
        """
        for _i in range(startup_period):
            try:
                (await self.get("/.well-known/ready")).raise_for_status()
                return
            except (ConnectError, ReadError, TimeoutError, HTTPStatusError):
                time.sleep(1)

        try:
            (await self.get("/.well-known/ready")).raise_for_status()
            return
        except (ConnectError, ReadError, TimeoutError, HTTPStatusError) as error:
            raise WeaviateStartUpError(
                f"Weaviate did not start up in {startup_period} seconds. Either the Weaviate URL {self.url} is wrong or Weaviate did not start up in the interval given in 'startup_period'."
            ) from error

    def _prepare_grpc_headers(self) -> None:
        self.__metadata_list: List[Tuple[str, str]] = []
        if len(self.additional_headers):
            for key, val in self.additional_headers.items():
                if val is not None:
                    self.__metadata_list.append((key.lower(), val))

        if self._auth is not None:
            if isinstance(self._auth, AuthApiKey):
                if (
                    "X-Weaviate-Cluster-URL" in self._headers
                    and "X-Weaviate-Api-Key" in self._headers
                ):
                    self.__metadata_list.append(
                        ("x-weaviate-cluster-url", self._headers["X-Weaviate-Cluster-URL"])
                    )
                    self.__metadata_list.append(
                        ("x-weaviate-api-key", self._headers["X-Weaviate-Api-Key"])
                    )
                self.__metadata_list.append(("authorization", "Bearer " + self._auth.api_key))
            else:
                self.__metadata_list.append(
                    ("authorization", "dummy_will_be_refreshed_for_each_call")
                )

        if len(self.__metadata_list) > 0:
            self.__grpc_headers: Optional[Tuple[Tuple[str, str], ...]] = tuple(self.__metadata_list)
        else:
            self.__grpc_headers = None

    def grpc_headers(self) -> Optional[Tuple[Tuple[str, str], ...]]:
        if self._auth is None or isinstance(self._auth, AuthApiKey):
            return self.__grpc_headers

        assert self.__grpc_headers is not None
        access_token = self.get_current_bearer_token()
        # auth is last entry in list, rest is static
        self.__metadata_list[len(self.__metadata_list) - 1] = ("authorization", access_token)
        return tuple(self.__metadata_list)

    async def _ping_grpc(self) -> None:
        """Performs a grpc health check and raises WeaviateGRPCUnavailableError if not."""
        if not self.is_connected():
            raise WeaviateClosedClientError()
        assert self._grpc_channel is not None
        try:
            res: health_pb2.HealthCheckResponse = await self._grpc_channel.unary_unary(
                "/grpc.health.v1.Health/Check",
                request_serializer=health_pb2.HealthCheckRequest.SerializeToString,
                response_deserializer=health_pb2.HealthCheckResponse.FromString,
            )(health_pb2.HealthCheckRequest(), timeout=self.timeout_config.init)
            if res.status != health_pb2.HealthCheckResponse.SERVING:
                raise WeaviateGRPCUnavailableError(
                    f"v{self.server_version}", self._connection_params._grpc_address
                )
        except Exception as e:
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
