"""
Client class definition.
"""

from abc import abstractmethod
from typing import (
    Any,
    Generic,
    Optional,
    Tuple,
    Union,
    Dict,
    Type,
    TypeVar,
)

from httpx import Response

from weaviate.collections.classes.internal import _GQLEntryReturnType, _RawGQLReturn

from weaviate.integrations import _Integrations

from .auth import AuthCredentials
from .config import AdditionalConfig
from .connect.v4 import Connection, ConnectionAsync, ConnectionSync
from .connect.base import (
    ConnectionParams,
    ProtocolParams,
)
from .connect.executor import aresult, do_nothing, result, ExecutorResult, execute
from .connect.v4 import _ExpectedStatusCodes
from .embedded import EmbeddedOptions, EmbeddedV4
from .types import NUMBER
from .util import _decode_json_response_dict
from .validator import _validate_input, _ValidateArgument

TIMEOUT_TYPE = Union[Tuple[NUMBER, NUMBER], NUMBER]


class _WeaviateClientExecutor:
    async def __close_async(self, connection: ConnectionAsync) -> None:
        await aresult(connection.close("async"))

    def close(self, connection: Connection) -> ExecutorResult[None,]:
        if isinstance(connection, ConnectionAsync):
            return self.__close_async(connection)
        return result(connection.close("sync"))

    def connect(self, connection: Connection) -> ExecutorResult[None]:
        return execute(
            response_callback=lambda _: None,
            method=connection.connect,
        )

    def is_live(self, connection: Connection) -> ExecutorResult[bool]:
        def resp(res: Response) -> bool:
            return res.status_code == 200

        def exc(e: Exception) -> bool:
            print(e)
            return False

        return execute(
            response_callback=resp,
            exception_callback=exc,
            method=connection.get,
            path="/.well-known/live",
        )

    def is_ready(self, connection: Connection) -> ExecutorResult[bool]:
        def resp(res: Response) -> bool:
            return res.status_code == 200

        def exc(e: Exception) -> bool:
            print(e)
            return False

        return execute(
            response_callback=resp,
            exception_callback=exc,
            method=connection.get,
            path="/.well-known/ready",
        )

    def graphql_raw_query(
        self, connection: Connection, gql_query: str
    ) -> ExecutorResult[_RawGQLReturn]:
        _validate_input(_ValidateArgument([str], "gql_query", gql_query))
        json_query = {"query": gql_query}

        def resp(response: Response) -> _RawGQLReturn:
            res = _decode_json_response_dict(response, "GQL query")
            assert res is not None

            errors: Optional[Dict[str, Any]] = res.get("errors")
            data_raw: Optional[Dict[str, _GQLEntryReturnType]] = res.get("data")

            if data_raw is not None:
                return _RawGQLReturn(
                    aggregate=data_raw.get("Aggregate", {}),
                    explore=data_raw.get("Explore", {}),
                    get=data_raw.get("Get", {}),
                    errors=errors,
                )

            return _RawGQLReturn(aggregate={}, explore={}, get={}, errors=errors)

        def exc(e: Exception) -> _RawGQLReturn:
            raise e

        return execute(
            response_callback=resp,
            exception_callback=exc,
            method=connection.post,
            path="/graphql",
            weaviate_object=json_query,
            error_msg="Raw GQL query failed",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="GQL query"),
            is_gql_query=True,
        )

    def get_meta(self, connection: Connection) -> ExecutorResult[dict]:
        return execute(
            response_callback=do_nothing,
            method=connection.get_meta,
        )

    def get_open_id_configuration(
        self, connection: Connection
    ) -> ExecutorResult[Optional[Dict[str, Any]]]:
        return execute(
            response_callback=do_nothing,
            method=connection.get_open_id_configuration,
        )


C = TypeVar("C", ConnectionAsync, ConnectionSync)


class _WeaviateClientBase(Generic[C]):
    _connection: C
    _connection_type: Type[C]
    _executor = _WeaviateClientExecutor()

    def __init__(
        self,
        connection_params: Optional[ConnectionParams] = None,
        embedded_options: Optional[EmbeddedOptions] = None,
        auth_client_secret: Optional[AuthCredentials] = None,
        additional_headers: Optional[dict] = None,
        additional_config: Optional[AdditionalConfig] = None,
        skip_init_checks: bool = False,
    ) -> None:
        """Initialise a WeaviateClient/WeaviateClientAsync class instance to use when interacting with Weaviate.

        Use this specific initializer when you want to create a custom Client specific to your Weaviate setup.

        To simplify connections to Weaviate Cloud or local instances, use the weaviate.connect_to_weaviate_cloud
        or weaviate.connect_to_local helper functions.

        Arguments:
            - `connection_params`: `weaviate.connect.ConnectionParams` or None, optional
                - The connection parameters to use for the underlying HTTP requests.
            - `embedded_options`: `weaviate.EmbeddedOptions` or None, optional
                - The options to use when provisioning an embedded Weaviate instance.
            - `auth_client_secret`: `weaviate.AuthCredentials` or None, optional
                - Authenticate to weaviate by using one of the given authentication modes:
                    - `weaviate.auth.AuthBearerToken` to use existing access and (optionally, but recommended) refresh tokens
                    - `weaviate.auth.AuthClientPassword` to use username and password for oidc Resource Owner Password flow
                    - `weaviate.auth.AuthClientCredentials` to use a client secret for oidc client credential flow
            - `additional_headers`: `dict` or None, optional
                - Additional headers to include in the requests.
                    - Can be used to set OpenAI/HuggingFace/Cohere etc. keys.
                    - [Here](https://weaviate.io/developers/weaviate/modules/reader-generator-modules/generative-openai#providing-the-key-to-weaviate) is an
                    example of how to set API keys within this parameter.
            - `additional_config`: `weaviate.AdditionalConfig` or None, optional
                - Additional and advanced configuration options for Weaviate.
            - `skip_init_checks`: `bool`, optional
                - If set to `True` then the client will not perform any checks including ensuring that weaviate has started. This is useful for air-gapped environments and high-performance setups.
        """
        connection_params, embedded_db = self.__parse_connection_params_and_embedded_db(
            connection_params, embedded_options
        )
        config = additional_config or AdditionalConfig()

        self._connection = (
            self._connection_type(  # pyright: ignore reportIncompatibleVariableOverride
                connection_params=connection_params,
                auth_client_secret=auth_client_secret,
                timeout_config=config.timeout,
                additional_headers=additional_headers,
                embedded_db=embedded_db,
                connection_config=config.connection,
                proxies=config.proxies,
                trust_env=config.trust_env,
                skip_init_checks=skip_init_checks,
            )
        )

        self.integrations = _Integrations(self._connection)

    def __parse_connection_params_and_embedded_db(
        self,
        connection_params: Optional[ConnectionParams],
        embedded_options: Optional[EmbeddedOptions],
    ) -> Tuple[ConnectionParams, Optional[EmbeddedV4]]:
        if connection_params is None and embedded_options is None:
            raise TypeError("Either connection_params or embedded_options must be present.")
        elif connection_params is not None and embedded_options is not None:
            raise TypeError(
                f"connection_params is not expected to be set when using embedded_options but connection_params was {connection_params}"
            )

        if embedded_options is not None:
            _validate_input(
                _ValidateArgument([EmbeddedOptions], "embedded_options", embedded_options)
            )

            embedded_db = EmbeddedV4(options=embedded_options)
            embedded_db.start()
            return (
                ConnectionParams(
                    http=ProtocolParams(
                        host="localhost", port=embedded_db.options.port, secure=False
                    ),
                    grpc=ProtocolParams(
                        host="localhost", port=embedded_options.grpc_port, secure=False
                    ),
                ),
                embedded_db,
            )

        if not isinstance(connection_params, ConnectionParams):
            raise TypeError(
                f"connection_params is expected to be a ConnectionParams object but is {type(connection_params)}"
            )

        return connection_params, None

    def is_connected(self) -> bool:
        """Check if the client is connected to Weaviate.

        Returns:
            `bool`
                `True` if the client is connected to Weaviate with an open connection pool, `False` otherwise.
        """
        return self._connection.is_connected()

    @abstractmethod
    def connect(self) -> ExecutorResult[None]:
        """
        Connect to Weaviate.

        It is required that this method is called before any other operations can be made successfully.
        If not done so, exepctions will be raised.
        """
        raise NotImplementedError()

    @abstractmethod
    def close(self) -> ExecutorResult[None]:
        """
        Close the connection to Weaviate.

        This method should be called when the client is no longer needed to free up resources.
        """
        raise NotImplementedError()

    @abstractmethod
    def is_live(self) -> ExecutorResult[bool]:
        raise NotImplementedError()

    @abstractmethod
    def is_ready(self) -> ExecutorResult[bool]:
        raise NotImplementedError()

    @abstractmethod
    def graphql_raw_query(self, gql_query: str) -> ExecutorResult[_RawGQLReturn]:
        """Allows to send graphQL string queries, this should only be used for weaviate-features that are not yet supported.

        Be cautious of injection risks when generating query strings.

        Arguments:
            `gql_query`
                GraphQL query as a string.

        Returns:
            A dict with the response from the GraphQL query.

        Raises
            `TypeError`
                If 'gql_query' is not of type str.
            `weaviate.WeaviateConnectionError`
                If the network connection to weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If weaviate reports a none OK status.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_meta(self) -> ExecutorResult[dict]:
        """
        Get the meta endpoint description of weaviate.

        Returns:
            `dict`
                The `dict` describing the weaviate configuration.

        Raises:
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a none OK status.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_open_id_configuration(self) -> ExecutorResult[Optional[Dict[str, Any]]]:
        """
        Get the openid-configuration.

        Returns
            `dict`
                The configuration or `None` if not configured.

        Raises
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a none OK status.
        """
        raise NotImplementedError()
