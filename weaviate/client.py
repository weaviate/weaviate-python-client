"""
Client class definition.
"""

from typing import Generic, Optional, Tuple, TypeVar, Union, Dict, Any

from httpx import HTTPError as HttpxError
from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.backup.backup import _Backup
from weaviate.collections.classes.internal import _GQLEntryReturnType, _RawGQLReturn

from .auth import AuthCredentials
from .backup import Backup
from .batch import Batch
from .classification import Classification
from .cluster import Cluster
from .collections.collections import _Collections
from .collections.batch.client import _BatchClientWrapper
from .collections.cluster import _Cluster
from .config import AdditionalConfig, Config
from .connect import Connection, ConnectionV4
from .connect.base import (
    ConnectionParams,
    ProtocolParams,
    TIMEOUT_TYPE_RETURN,
)
from .connect.v4 import _ExpectedStatusCodes
from .contextionary import Contextionary
from .data import DataObject
from .embedded import EmbeddedV3, EmbeddedV4, EmbeddedOptions
from .exceptions import (
    UnexpectedStatusCodeError,
    WeaviateClosedClientError,
    WeaviateConnectionError,
)
from .gql import Query
from .schema import Schema
from .types import NUMBER
from .util import _decode_json_response_dict, _get_valid_timeout_config, _type_request_response
from .validator import _validate_input, _ValidateArgument
from .warnings import _Warnings

TIMEOUT_TYPE = Union[Tuple[NUMBER, NUMBER], NUMBER]

C = TypeVar("C", Connection, ConnectionV4)


class _ClientBase(Generic[C]):
    _connection: C

    def is_ready(self) -> bool:
        """
        Ping Weaviate's ready state

        Returns:
            `bool`
                `True` if Weaviate is ready to accept requests,
                `False` otherwise.
        """

        try:
            response = self._connection.get(path="/.well-known/ready")
            if response.status_code == 200:
                return True
            return False
        except (
            HttpxError,
            RequestsConnectionError,
            UnexpectedStatusCodeError,
            WeaviateClosedClientError,
            WeaviateConnectionError,
        ):
            return False

    def is_live(self) -> bool:
        """
        Ping Weaviate's live state.

        Returns:
            `bool`
                `True` if weaviate is live and should not be killed,
                `False` otherwise.
        """

        response = self._connection.get(path="/.well-known/live")
        if response.status_code == 200:
            return True
        return False

    def get_meta(self) -> dict:
        """
        Get the meta endpoint description of weaviate.

        Returns:
            `dict`
                The `dict` describing the weaviate configuration.

        Raises:
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a none OK status.
        """

        return self._connection.get_meta()

    def get_open_id_configuration(self) -> Optional[Dict[str, Any]]:
        """
        Get the openid-configuration.

        Returns
            `dict`
                The configuration or `None` if not configured.

        Raises
            `weaviate.UnexpectedStatusCodeError`
                If Weaviate reports a none OK status.
        """

        response = self._connection.get(path="/.well-known/openid-configuration")
        if response.status_code == 200:
            return _type_request_response(response.json())
        if response.status_code == 404:
            return None
        raise UnexpectedStatusCodeError("Meta endpoint", response)


class WeaviateClient(_ClientBase[ConnectionV4]):
    """
    The v4 Python-native Weaviate Client class that encapsulates Weaviate functionalities in one object.

    WARNING: This client is only compatible with Weaviate v1.23.6 and higher!

    A Client instance creates all the needed objects to interact with Weaviate, and connects all of
    them to the same Weaviate instance. See below the Attributes of the Client instance. For the
    per attribute functionality see that attribute's documentation.

    Attributes:
        `backup`
            A `Backup` object instance connected to the same Weaviate instance as the Client.
        `batch`
            A `_Batch` object instance connected to the same Weaviate instance as the Client.
        `classification`
            A `Classification` object instance connected to the same Weaviate instance as the Client.
        `cluster`
            A `Cluster` object instance connected to the same Weaviate instance as the Client.
        `collections`
            A `_Collections` object instance connected to the same Weaviate instance as the Client.
    """

    def __init__(
        self,
        connection_params: Optional[ConnectionParams] = None,
        embedded_options: Optional[EmbeddedOptions] = None,
        auth_client_secret: Optional[AuthCredentials] = None,
        additional_headers: Optional[dict] = None,
        additional_config: Optional[AdditionalConfig] = None,
        skip_init_checks: bool = False,
    ) -> None:
        """Initialise a WeaviateClient class instance to use when interacting with Weaviate.

        Use this specific initializer when you want to create a custom Client specific to your Weaviate setup.

        If you want to get going quickly connecting to WCS or a local instance then use the `weaviate.connect_to_wcs` or
        `weaviate.connect_to_local` helper functions instead.

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
        self.__skip_init_checks = skip_init_checks

        self._connection = ConnectionV4(  # pyright: ignore reportIncompatibleVariableOverride
            connection_params=connection_params,
            auth_client_secret=auth_client_secret,
            timeout_config=config.timeout,
            additional_headers=additional_headers,
            embedded_db=embedded_db,
            connection_config=config.connection,
            proxies=config.proxies,
            trust_env=config.trust_env,
        )

        self.batch = _BatchClientWrapper(self._connection, consistency_level=None)
        """This namespace contains all the functionality to upload data in batches to Weaviate for all collections and tenants."""
        self.backup = _Backup(self._connection)
        """This namespace contains all functionality to backup data."""
        self.cluster = _Cluster(self._connection)
        """This namespace contains all functionality to inspect the connected Weaviate cluster."""
        self.collections = _Collections(self._connection)
        """This namespace contains all the functionality to manage Weaviate data collections. It is your main entry point for all collection-related functionality.

        Use it to retrieve collection objects using `client.collections.get("MyCollection")` or to create new collections using `client.collections.create("MyCollection", ...)`.
        """

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

    def __enter__(self) -> "WeaviateClient":
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.close()

    def close(self) -> None:
        """In order to clean up any resources used by the client, call this method when you are done with it.

        If you do not do this, memory leaks may occur due to stale connections.
        This method also closes the embedded database if one was started."""
        self._connection.close()

    def connect(self) -> None:
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
        self._connection.connect(self.__skip_init_checks)

    def is_connected(self) -> bool:
        """Check if the client is connected to Weaviate.

        Returns:
            `bool`
                `True` if the client is connected to Weaviate with an open connection pool, `False` otherwise.
        """
        return self._connection.is_connected()

    def is_live(self) -> bool:
        try:
            self._connection._ping_grpc()
        except Exception:
            return False
        return super().is_live()

    def graphql_raw_query(self, gql_query: str) -> _RawGQLReturn:
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

        response = self._connection.post(
            path="/graphql",
            weaviate_object=json_query,
            error_msg="Raw GQL query failed",
            status_codes=_ExpectedStatusCodes(ok_in=[200], error="GQL query"),
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


class Client(_ClientBase[Connection]):
    """
    The v3 Python-native Weaviate Client class that encapsulates Weaviate functionalities in one object.
    A Client instance creates all the needed objects to interact with Weaviate, and connects all of
    them to the same Weaviate instance. See below the Attributes of the Client instance. For the
    per attribute functionality see that attribute's documentation.

    Attributes
    ----------
    backup : weaviate.backup.Backup
        A Backup object instance connected to the same Weaviate instance as the Client.
    batch : weaviate.batch.Batch
        A Batch object instance connected to the same Weaviate instance as the Client.
    classification : weaviate.classification.Classification
        A Classification object instance connected to the same Weaviate instance as the Client.
    cluster : weaviate.cluster.Cluster
        A Cluster object instance connected to the same Weaviate instance as the Client.
    contextionary : weaviate.contextionary.Contextionary
        A Contextionary object instance connected to the same Weaviate instance as the Client.
    data_object : weaviate.data.DataObject
        A DataObject object instance connected to the same Weaviate instance as the Client.
    schema : weaviate.schema.Schema
        A Schema object instance connected to the same Weaviate instance as the Client.
    query : weaviate.gql.Query
        A Query object instance connected to the same Weaviate instance as the Client.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        auth_client_secret: Optional[AuthCredentials] = None,
        timeout_config: TIMEOUT_TYPE = (10, 60),
        proxies: Union[dict, str, None] = None,
        trust_env: bool = False,
        additional_headers: Optional[dict] = None,
        startup_period: Optional[int] = None,
        embedded_options: Optional[EmbeddedOptions] = None,
        additional_config: Optional[Config] = None,
    ) -> None:
        """Initialize a Client class instance to use when interacting with Weaviate.

        Arguments:
        ----------
        url : str or None, optional
            The connection string to the REST API of Weaviate.
        auth_client_secret : weaviate.AuthCredentials or None, optional
        # fmt: off
            Authenticate to weaviate by using one of the given authentication modes:
            - weaviate.auth.AuthBearerToken to use existing access and (optionally, but recommended) refresh tokens
            - weaviate.auth.AuthClientPassword to use username and password for oidc Resource Owner Password flow
            - weaviate.auth.AuthClientCredentials to use a client secret for oidc client credential flow

        # fmt: on
        timeout_config : tuple(Real, Real) or Real, optional
            Set the timeout configuration for all requests to the Weaviate server. It can be a
            real number or, a tuple of two real numbers: (connect timeout, read timeout).
            If only one real number is passed then both connect and read timeout will be set to
            that value, by default (2, 20).
        proxies : dict, str or None, optional
            Proxies to be used for requests. Are used by both 'requests' and 'aiohttp'. Can be
            passed as a dict ('requests' format:
            https://docs.python-requests.org/en/stable/user/advanced/#proxies), str (HTTP/HTTPS
            protocols are going to use this proxy) or None.
            Default None.
        trust_env : bool, optional
            Whether to read proxies from the ENV variables: (HTTP_PROXY or http_proxy, HTTPS_PROXY
            or https_proxy). Default False.
            NOTE: 'proxies' has priority over 'trust_env', i.e. if 'proxies' is NOT None,
            'trust_env' is ignored.
        additional_headers : dict or None
            Additional headers to include in the requests.
            Can be used to set OpenAI/HuggingFace keys. OpenAI/HuggingFace key looks like this:
                {"X-OpenAI-Api-Key": "<THE-KEY>"}, {"X-HuggingFace-Api-Key": "<THE-KEY>"}
            by default None
        startup_period : int or None
            deprecated, has no effect
        embedded_options : weaviate.embedded.EmbeddedOptions or None, optional
            Create an embedded Weaviate cluster inside the client
            - You can pass weaviate.embedded.EmbeddedOptions() with default values
            - Take a look at the attributes of weaviate.embedded.EmbeddedOptions to see what is configurable
        additional_config: weaviate.Config, optional
            Additional and advanced configuration options for weaviate.

        Raises:
        -------
            `TypeError`
                If arguments are of a wrong data type.
        """
        _Warnings.weaviate_v3_client_is_deprecated()

        config = Config() if additional_config is None else additional_config
        url, embedded_db = self.__parse_url_and_embedded_db(url, embedded_options)

        self._connection = Connection(
            url=url,
            auth_client_secret=auth_client_secret,
            timeout_config=_get_valid_timeout_config(timeout_config),
            proxies=proxies,
            trust_env=trust_env,
            additional_headers=additional_headers,
            startup_period=startup_period,
            embedded_db=embedded_db,
            grcp_port=config.grpc_port_experimental,
            connection_config=config.connection_config,
        )
        self.classification = Classification(self._connection)
        self.schema = Schema(self._connection)
        self.contextionary = Contextionary(self._connection)
        self.batch = Batch(self._connection)
        self.data_object = DataObject(self._connection)
        self.query = Query(self._connection)
        self.backup = Backup(self._connection)
        self.cluster = Cluster(self._connection)

    def __parse_url_and_embedded_db(
        self, url: Optional[str], embedded_options: Optional[EmbeddedOptions]
    ) -> Tuple[str, Optional[EmbeddedV3]]:
        if embedded_options is None and url is None:
            raise TypeError("Either url or embedded options must be present.")
        elif embedded_options is not None and url is not None:
            raise TypeError(
                f"URL is not expected to be set when using embedded_options but URL was {url}"
            )

        if embedded_options is not None:
            embedded_db = EmbeddedV3(options=embedded_options)
            embedded_db.start()
            return f"http://localhost:{embedded_db.options.port}", embedded_db

        if not isinstance(url, str):
            raise TypeError(f"URL is expected to be string but is {type(url)}")
        return url.strip("/"), None

    @property
    def timeout_config(self) -> TIMEOUT_TYPE_RETURN:
        """
        Getter/setter for `timeout_config`.

        Parameters
        ----------
        timeout_config : tuple(float, float) or float, optional
            For Getter only: Set the timeout configuration for all requests to the Weaviate server.
            It can be a real number or, a tuple of two real numbers:
                    (connect timeout, read timeout).
            If only one real number is passed then both connect and read timeout will be set to
            that value.

        Returns
        -------
        Tuple[float, float]
            For Getter only: Requests Timeout configuration.
        """

        return self._connection.timeout_config

    @timeout_config.setter
    def timeout_config(self, timeout_config: TIMEOUT_TYPE) -> None:
        """
        Setter for `timeout_config`. (docstring should be only in the Getter)
        """

        self._connection.timeout_config = _get_valid_timeout_config(timeout_config)

    def __del__(self) -> None:
        # in case an exception happens before definition of the client
        if hasattr(self, "_connection"):
            self._connection.close()
