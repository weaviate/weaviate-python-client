"""
Client class definition.
"""
from typing import Literal, Optional, Tuple, Type, Union, Dict, Any, overload

from requests.exceptions import ConnectionError as RequestsConnectionError

from .auth import AuthCredentials, AuthApiKey
from .backup import Backup
from .batch import Batch
from .classification import Classification
from .cluster import Cluster
from .collection import _Collection
from .collection.collection_model import _CollectionModel
from .config import Config
from .connect.connection import (
    Connection,
    ConnectionParams,
    GRPCConnection,
    ProtocolParams,
    TIMEOUT_TYPE_RETURN,
)
from .contextionary import Contextionary
from .data import DataObject
from .embedded import EmbeddedDB, EmbeddedOptions
from .exceptions import UnexpectedStatusCodeException
from .gql import Query
from .schema import Schema
from .util import _get_valid_timeout_config, _type_request_response
from .types import NUMBER

TIMEOUT_TYPE = Union[Tuple[NUMBER, NUMBER], NUMBER]


class _ClientBase:
    _connection: Connection

    def is_ready(self) -> bool:
        """
        Ping Weaviate's ready state

        Returns
        -------
        bool
            True if Weaviate is ready to accept requests,
            False otherwise.
        """

        try:
            response = self._connection.get(path="/.well-known/ready")
            if response.status_code == 200:
                return True
            return False
        except RequestsConnectionError:
            return False

    def is_live(self) -> bool:
        """
        Ping Weaviate's live state.

        Returns
        --------
        bool
            True if weaviate is live and should not be killed,
            False otherwise.
        """

        response = self._connection.get(path="/.well-known/live")
        if response.status_code == 200:
            return True
        return False

    def get_meta(self) -> dict:
        """
        Get the meta endpoint description of weaviate.

        Returns
        -------
        dict
            The dict describing the weaviate configuration.

        Raises
        ------
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """

        return self._connection.get_meta()

    def get_open_id_configuration(self) -> Optional[Dict[str, Any]]:
        """
        Get the openid-configuration.

        Returns
        -------
        dict
            The configuration or None if not configured.

        Raises
        ------
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """

        response = self._connection.get(path="/.well-known/openid-configuration")
        if response.status_code == 200:
            return _type_request_response(response.json())
        if response.status_code == 404:
            return None
        raise UnexpectedStatusCodeException("Meta endpoint", response)

    @staticmethod
    def _parse_connection_params_and_embedded_db(
        connection_params: Optional[ConnectionParams], embedded_options: Optional[EmbeddedOptions]
    ) -> Tuple[ConnectionParams, Optional[EmbeddedDB]]:
        if connection_params is None and embedded_options is None:
            raise TypeError("Either connection_params or embedded_options must be present.")
        elif connection_params is not None and embedded_options is not None:
            raise TypeError(
                f"connection_params is not expected to be set when using embedded_options but connection_params was {connection_params}"
            )

        if embedded_options is not None:
            embedded_db = EmbeddedDB(options=embedded_options)
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

    @staticmethod
    def _parse_url_and_embedded_db(
        url: Optional[str], grpc_port: Optional[int], embedded_options: Optional[EmbeddedOptions]
    ) -> Tuple[ConnectionParams, Optional[EmbeddedDB]]:
        if embedded_options is None and url is None:
            raise TypeError("Either url or embedded options must be present.")
        elif embedded_options is not None and url is not None:
            raise TypeError(
                f"URL is not expected to be set when using embedded_options but URL was {url}"
            )

        if embedded_options is not None:
            embedded_db = EmbeddedDB(options=embedded_options)
            embedded_db.start()
            return (
                ConnectionParams.from_url(
                    f"http://localhost:{embedded_db.options.port}", grpc_port
                ),
                embedded_db,
            )

        if not isinstance(url, str):
            raise TypeError(f"URL is expected to be string but is {type(url)}")
        return ConnectionParams.from_url(url, grpc_port), None

    def __del__(self) -> None:
        # in case an exception happens before definition of these members
        if hasattr(self, "_connection"):
            self._connection.close()


class WeaviateClient(_ClientBase):
    def __init__(
        self,
        connection_params: Optional[ConnectionParams] = None,
        auth_client_secret: Optional[AuthCredentials] = None,
        additional_headers: Optional[Dict[str, Any]] = None,
        embedded_options: Optional[EmbeddedOptions] = None,
    ) -> None:
        connection_params, embedded_db = self._parse_connection_params_and_embedded_db(
            connection_params, embedded_options
        )
        config = Config()

        self._connection = GRPCConnection(
            connection_params=connection_params,
            auth_client_secret=auth_client_secret,
            timeout_config=_get_valid_timeout_config((10, 60)),
            additional_headers=additional_headers,
            embedded_db=embedded_db,
            connection_config=config.connection_config,
            proxies=None,
            trust_env=False,
            startup_period=5,
        )
        self.classification = Classification(self._connection)
        self.schema = Schema(self._connection)
        self.contextionary = Contextionary(self._connection)
        self.batch = Batch(self._connection)
        self.data_object = DataObject(self._connection)
        self.query = Query(self._connection)
        self.backup = Backup(self._connection)
        self.cluster = Cluster(self._connection)
        self.collection = _Collection(self._connection)
        self._collection_model = _CollectionModel(self._connection)  # experimental


class Client(_ClientBase):
    """
    A python native Weaviate Client class that encapsulates Weaviate functionalities in one object.
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
        startup_period: Optional[int] = 5,
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
            How long the client will wait for Weaviate to start before raising a RequestsConnectionError.
            If None, the client won't wait at all. Default timeout is 5s.
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
        config = Config() if additional_config is None else additional_config
        connection_params, embedded_db = self._parse_url_and_embedded_db(
            url, config.grpc_port_experimental, embedded_options
        )

        self._connection = Connection(
            connection_params=connection_params,
            auth_client_secret=auth_client_secret,
            timeout_config=_get_valid_timeout_config(timeout_config),
            proxies=proxies,
            trust_env=trust_env,
            additional_headers=additional_headers,
            startup_period=startup_period,
            embedded_db=embedded_db,
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


class ClientFactory:
    """Use this factory class to create `weaviate.WeaviateClient` (v4) or `weaviate.Client` (v3) objects that are automatically
    configured to connect to your custom-deployed Weaviate instance.

    If you find that you need more fine-grained control over the connection parameters, you can
    also instantiate a `weaviate.Client` object directly yourself using the `weaviate.ConnectionParams.from_params`
    method to specify your unique HTTP & gRPC setup.

    These factory methods are meant as short-cuts for the principal use-cases to ease friction
    when getting started with Weaviate.
    """

    @overload
    @classmethod
    def connect_to_wcs(cls, cluster_id: str, api_key: str, version: Literal["v3"]) -> Client:
        ...

    @overload
    @classmethod
    def connect_to_wcs(
        cls, cluster_id: str, api_key: str, version: Literal["v4"]
    ) -> WeaviateClient:
        ...

    @classmethod
    def connect_to_wcs(
        cls, cluster_id: str, api_key: str, version: Literal["v3", "v4"] = "v4"
    ) -> Union[Client, WeaviateClient]:
        """
        Connect to your own Weaviate Cloud Service (WCS) instance.

        Arguments:
            `cluster_id`
                The cluster id to connect to.
            `api_key`
                The api key to use for authentication.
            `version`
                The version of the Weaviate Python Client to use. Defaults to v4.

        Returns
            `weaviate.Client`
                The client connected to the cluster with the required parameters set appropriately.
        """
        if version == "v4":
            return WeaviateClient(
                connection_params=ConnectionParams(
                    http=ProtocolParams(
                        host=f"{cluster_id}.weaviate.network", port=443, secure=True
                    ),
                    grpc=ProtocolParams(
                        host=f"{cluster_id}.weaviate.network", port=50051, secure=True
                    ),
                ),
                auth_client_secret=AuthApiKey(api_key),
            )
        else:
            return Client(
                f"https://{cluster_id}.weaviate.network",
                additional_config=Config(
                    grpc_port_experimental=50051,
                    grpc_secure_experimental=True,
                ),
                auth_client_secret=AuthApiKey(api_key),
            )

    @overload
    @classmethod
    def connect_to_local(
        cls,
        host: str = "localhost",
        port: int = 8080,
        grpc_port: int = 50051,
        *,
        version: Literal["v3"],
    ) -> Client:
        ...

    @overload
    @classmethod
    def connect_to_local(
        cls,
        host: str = "localhost",
        port: int = 8080,
        grpc_port: int = 50051,
        version: Literal["v4"] = "v4",
    ) -> WeaviateClient:
        ...

    @classmethod
    def connect_to_local(
        cls,
        host: str = "localhost",
        port: int = 8080,
        grpc_port: int = 50051,
        version: Literal["v3", "v4"] = "v4",
    ) -> Union[Client, WeaviateClient]:
        """
        Connect to a local Weaviate instance deployed using Docker compose with standard port configurations.

        Arguments:
            `schema`
                The schema to use for the underlying REST & GraphQL API calls.
            `host`
                The host to use for the underlying REST & GraphQL API calls.
            `port`
                The port to use for the underlying REST & GraphQL API calls.
            `grpc_port`
                The port to use for the underlying gRPC API.
            `version`
                The version of the Weaviate Python Client to use. Defaults to v4.

        Returns
            `weaviate.Client`
                The client connected to the local instance with default parameters set as:
        """
        if version == "v4":
            return WeaviateClient(
                connection_params=ConnectionParams(
                    http=ProtocolParams(host=host, port=port, secure=False),
                    grpc=ProtocolParams(host=host, port=grpc_port, secure=False),
                ),
            )
        else:
            return Client(
                "http://localhost:8080",
                additional_config=Config(
                    grpc_port_experimental=50051,
                    grpc_secure_experimental=False,
                ),
            )

    @overload
    @classmethod
    def connect_to_embedded(
        cls, port: int = 8079, grpc_port: int = 50051, *, version: Literal["v3"]
    ) -> Client:
        ...

    @overload
    @classmethod
    def connect_to_embedded(
        cls, port: int = 8079, grpc_port: int = 50051, version: Literal["v4"] = "v4"
    ) -> WeaviateClient:
        ...

    @classmethod
    def connect_to_embedded(
        cls, port: int = 8079, grpc_port: int = 50051, version: Literal["v3", "v4"] = "v4"
    ) -> Union[Client, WeaviateClient]:
        """
        Connect to an embedded Weaviate instance.

        Arguments:
            `port`
                The port to use for the underlying REST & GraphQL API calls.
            `grpc_port`
                The port to use for the underlying gRPC API.
            `version`
                The version of the Weaviate Python Client to use. Defaults to v4.

        Returns
            `weaviate.Client`
                The client connected to the embedded instance with the required parameters set appropriately.
        """
        if version == "v4":
            client: Union[Type[Client], Type[WeaviateClient]] = WeaviateClient
        else:
            client = Client
        return client(
            embedded_options=EmbeddedOptions(
                port=port,
                grpc_port=grpc_port,
            )
        )

    @overload
    @classmethod
    def connect(
        cls,
        http_host: str,
        http_port: int,
        http_secure: bool,
        grpc_host: str,
        grpc_port: int,
        grpc_secure: bool,
        version: Literal["v3"],
    ) -> Client:
        ...

    @overload
    @classmethod
    def connect(
        cls,
        http_host: str,
        http_port: int,
        http_secure: bool,
        grpc_host: str,
        grpc_port: int,
        grpc_secure: bool,
        version: Literal["v4"] = "v4",
    ) -> WeaviateClient:
        ...

    @classmethod
    def connect(
        cls,
        http_host: str,
        http_port: int,
        http_secure: bool,
        grpc_host: str,
        grpc_port: int,
        grpc_secure: bool,
        version: Literal["v3", "v4"] = "v4",
    ) -> Union[Client, WeaviateClient]:
        """
        Connect to a Weaviate instance with custom connection parameters.

        Arguments:
            `http_host`
                The host to use for the underlying REST & GraphQL API calls.
            `http_port`
                The port to use for the underlying REST & GraphQL API calls.
            `http_secure`
                Whether to use https for the underlying REST & GraphQL API calls.
            `grpc_host`
                The host to use for the underlying gRPC API.
            `grpc_port`
                The port to use for the underlying gRPC API.
            `grpc_secure`
                Whether to use a secure channel for the underlying gRPC API.
            `version`
                The version of the Weaviate Python Client to use. Defaults to v4.

        Returns
            `weaviate.Client`
                The client connected to the instance with the required parameters set appropriately.
        """
        if version == "v4":
            return WeaviateClient(
                ConnectionParams.from_params(
                    http_host=http_host,
                    http_port=http_port,
                    http_secure=http_secure,
                    grpc_host=grpc_host,
                    grpc_port=grpc_port,
                    grpc_secure=grpc_secure,
                )
            )
        else:
            if grpc_host is not None and grpc_port != http_port:
                raise ValueError(
                    "When using the V3 client, grpc_host and http_host must be the same."
                )
            return Client(
                url=f"{'https' if http_secure else 'http'}://{http_host}:{http_port}",
                additional_config=Config(
                    grpc_port_experimental=grpc_port,
                    grpc_secure_experimental=grpc_secure,
                ),
            )
