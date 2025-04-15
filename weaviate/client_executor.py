"""Client class definition."""

from typing import (
    Any,
    Generic,
    Optional,
    Tuple,
    Union,
    Dict,
    Type,
)

from httpx import Response

from weaviate.collections.classes.internal import _GQLEntryReturnType, _RawGQLReturn

from weaviate.integrations import _Integrations

from .auth import AuthCredentials
from .config import AdditionalConfig
from .connect import executor
from .connect.v4 import ConnectionAsync
from .connect.base import (
    ConnectionParams,
    ProtocolParams,
)
from .connect.v4 import _ExpectedStatusCodes, ConnectionType
from .embedded import EmbeddedOptions, EmbeddedV4
from .types import NUMBER
from .util import _decode_json_response_dict
from .validator import _validate_input, _ValidateArgument

TIMEOUT_TYPE = Union[Tuple[NUMBER, NUMBER], NUMBER]


class _WeaviateClientExecutor(Generic[ConnectionType]):
    _connection_type: Type[ConnectionType]

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

        Args:
            connection_params: The connection parameters to use for the underlying HTTP requests.
            embedded_options: The options to use when provisioning an embedded Weaviate instance.
            auth_client_secret: Authenticate to weaviate by using one of the given authentication modes:
                - `weaviate.auth.AuthBearerToken` to use existing access and (optionally, but recommended) refresh tokens
                - `weaviate.auth.AuthClientPassword` to use username and password for oidc Resource Owner Password flow
                - `weaviate.auth.AuthClientCredentials` to use a client secret for oidc client credential flow
            additional_headers: Additional headers to include in the requests. Can be used to set OpenAI/HuggingFace/Cohere etc. keys.
                [Here](https://weaviate.io/developers/weaviate/modules/reader-generator-modules/generative-openai#providing-the-key-to-weaviate) is an
                example of how to set API keys within this parameter.
            additional_config: Additional and advanced configuration options for Weaviate.
            skip_init_checks: If set to `True` then the client will not perform any checks including ensuring that weaviate has started.
                This is useful for air-gapped environments and high-performance setups.
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

    async def __close_async(self) -> None:
        await executor.aresult(self._connection.close("async"))

    def close(self) -> executor.Result[None]:
        """In order to clean up any resources used by the client, call this method when you are done with it.

        If you do not do this, memory leaks may occur due to stale connections.
        This method also closes the embedded database if one was started.
        """
        if isinstance(self._connection, ConnectionAsync):
            return self.__close_async()
        return executor.result(self._connection.close("sync"))

    def connect(self) -> executor.Result[None]:
        """Connect to the Weaviate instance performing all the necessary checks.

        If you have specified `skip_init_checks` in the constructor then this method will not perform any runtime checks
        to ensure that Weaviate is running and ready to accept requests. This is useful for air-gapped environments and high-performance setups.

        This method is idempotent and will only perform the checks once. Any subsequent calls do nothing while `client.is_connected() == True`.

        Raises:
            weaviate.exceptions.WeaviateConnectionError: If the network connection to weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If weaviate reports a none OK status.
        """
        return executor.execute(
            response_callback=lambda _: None,
            method=self._connection.connect,
        )

    def is_live(self) -> executor.Result[bool]:
        def resp(res: Response) -> bool:
            return res.status_code == 200

        def exc(e: Exception) -> bool:
            print(e)
            return False

        return executor.execute(
            response_callback=resp,
            exception_callback=exc,
            method=self._connection.get,
            path="/.well-known/live",
        )

    def is_ready(self) -> executor.Result[bool]:
        def resp(res: Response) -> bool:
            return res.status_code == 200

        def exc(e: Exception) -> bool:
            print(e)
            return False

        return executor.execute(
            response_callback=resp,
            exception_callback=exc,
            method=self._connection.get,
            path="/.well-known/ready",
        )

    def graphql_raw_query(self, gql_query: str) -> executor.Result[_RawGQLReturn]:
        """Allows to send graphQL string queries, this should only be used for weaviate-features that are not yet supported.

        Be cautious of injection risks when generating query strings.

        Args:
            gql_query: GraphQL query as a string.

        Returns:
            A dict with the response from the GraphQL query.

        Raises:
            TypeError: If `gql_query` is not of type str.
            weaviate.exceptions.WeaviateConnectionError: If the network connection to weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If weaviate reports a none OK status.
        """
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

        return executor.execute(
            response_callback=resp,
            exception_callback=exc,
            method=self._connection.post,
            path="/graphql",
            weaviate_object=json_query,
            error_msg="Raw GQL query failed",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="GQL query"),
            is_gql_query=True,
        )

    def get_meta(self) -> executor.Result[dict]:
        """Get the meta endpoint description of weaviate.

        Returns:
            The `dict` describing the weaviate configuration.

        Raises:
            weaviate.exceptions.UnexpectedStatusCodeError: If Weaviate reports a none OK status.
        """
        return executor.execute(
            response_callback=executor.do_nothing,
            method=self._connection.get_meta,
        )

    def get_open_id_configuration(
        self,
    ) -> executor.Result[Optional[Dict[str, Any]]]:
        """Get the openid-configuration.

        Returns:
            The configuration or `None` if not configured.

        Raises:
            weaviate.exceptions.UnexpectedStatusCodeError: If Weaviate reports a none OK status.
        """
        return executor.execute(
            response_callback=executor.do_nothing,
            method=self._connection.get_open_id_configuration,
        )

    @executor.no_wrapping
    def is_connected(self) -> bool:
        """Check if the client is connected to Weaviate.

        Returns:
            `True` if the client is connected to Weaviate with an open connection pool, `False` otherwise.
        """
        return self._connection.is_connected()
