"""
Client class definition.
"""

import asyncio
from typing import Optional, Tuple, Union, Dict, Any


from weaviate.collections.classes.internal import _GQLEntryReturnType, _RawGQLReturn

from weaviate.integrations import _Integrations

from .auth import AuthCredentials
from .config import AdditionalConfig
from .connect import ConnectionV4
from .connect.base import (
    ConnectionParams,
    ProtocolParams,
)
from .connect.v4 import _ExpectedStatusCodes
from .embedded import EmbeddedOptions, EmbeddedV4
from .types import NUMBER
from .util import _decode_json_response_dict
from .validator import _validate_input, _ValidateArgument

TIMEOUT_TYPE = Union[Tuple[NUMBER, NUMBER], NUMBER]


class _WeaviateClientInit:
    _loop: Optional[asyncio.AbstractEventLoop]

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
        assert self._loop is not None, "Cannot initialize a WeaviateClient without an event loop."
        connection_params, embedded_db = self.__parse_connection_params_and_embedded_db(
            connection_params, embedded_options
        )
        config = additional_config or AdditionalConfig()

        self._skip_init_checks = skip_init_checks

        self._connection = ConnectionV4(  # pyright: ignore reportIncompatibleVariableOverride
            connection_params=connection_params,
            auth_client_secret=auth_client_secret,
            timeout_config=config.timeout,
            additional_headers=additional_headers,
            embedded_db=embedded_db,
            connection_config=config.connection,
            proxies=config.proxies,
            trust_env=config.trust_env,
            loop=self._loop,
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


class _WeaviateClientBase(_WeaviateClientInit):
    async def close(self) -> None:
        """In order to clean up any resources used by the client, call this method when you are done with it.

        If you do not do this, memory leaks may occur due to stale connections.
        This method also closes the embedded database if one was started."""
        await self._connection.close()

    async def connect(self) -> None:
        """Connect to the Weaviate instance performing all the necessary checks.

        If you have specified `skip_init_checks` in the constructor then this method will not perform any runtime checks
        to ensure that Weaviate is running and ready to accept requests. This is useful for air-gapped environments and high-performance setups.

        This method is idempotent and will only perform the checks once. Any subsequent calls do nothing while `client.is_connected() == True`.

        Raises:
            `weaviate.WeaviateConnectionError`
                If the network connection to weaviate fails.
            `weaviate.UnexpectedStatusCodeException`
                If weaviate reports a none OK status.
        """
        if self._connection.is_connected():
            return
        await self._connection.connect(self._skip_init_checks)

    def is_connected(self) -> bool:
        """Check if the client is connected to Weaviate.

        Returns:
            `bool`
                `True` if the client is connected to Weaviate with an open connection pool, `False` otherwise.
        """
        return self._connection.is_connected()

    async def is_live(self) -> bool:
        try:
            results = await self._connection.get(path="/.well-known/live")
            if results.status_code == 200:
                return True
            return False
        except Exception as e:
            print(e)
            return False

    async def is_ready(self) -> bool:
        try:
            results = await self._connection.get(path="/.well-known/ready")
            if results.status_code == 200:
                return True
            return False
        except Exception as e:
            print(e)
            return False

    async def graphql_raw_query(self, gql_query: str) -> _RawGQLReturn:
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
        _validate_input(_ValidateArgument([str], "gql_query", gql_query))

        json_query = {"query": gql_query}

        response = await self._connection.post(
            path="/graphql",
            weaviate_object=json_query,
            error_msg="Raw GQL query failed",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="GQL query"),
            is_gql_query=True,
        )

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

    async def get_meta(self) -> dict:
        """
        Get the meta endpoint description of weaviate.

        Returns:
            `dict`
                The `dict` describing the weaviate configuration.

        Raises:
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a none OK status.
        """

        return await self._connection.get_meta()

    async def get_open_id_configuration(self) -> Optional[Dict[str, Any]]:
        """
        Get the openid-configuration.

        Returns
            `dict`
                The configuration or `None` if not configured.

        Raises
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a none OK status.
        """

        return await self._connection.get_open_id_configuration()
