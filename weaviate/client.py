"""
Client class definition.
"""
import asyncio
from typing import Optional, Tuple, Union, Dict, Any

from httpx import HTTPError as HttpxError
from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.backup.backup import _BackupAsync
from weaviate.backup.sync import _Backup


from weaviate import syncify
from .auth import AuthCredentials
from .backup import Backup
from .batch import Batch
from .classification import Classification

from .client_base import _WeaviateClientBase
from .cluster import Cluster
from .collections.collections.async_ import _CollectionsAsync
from .collections.collections.sync import _Collections
from .collections.batch.client import _BatchClientWrapper
from .collections.cluster import _Cluster, _ClusterAsync
from .config import AdditionalConfig, Config
from .connect import Connection
from .connect.base import (
    ConnectionParams,
    TIMEOUT_TYPE_RETURN,
)
from .contextionary import Contextionary
from .data import DataObject
from .embedded import EmbeddedOptions, EmbeddedV3
from .exceptions import (
    UnexpectedStatusCodeError,
    WeaviateClosedClientError,
    WeaviateConnectionError,
)
from .gql import Query
from .schema import Schema
from weaviate.event_loop import _EventLoopSingleton, _EventLoop
from .types import NUMBER
from .util import _get_valid_timeout_config, _type_request_response
from .warnings import _Warnings

TIMEOUT_TYPE = Union[Tuple[NUMBER, NUMBER], NUMBER]


@syncify.convert
class WeaviateClient(_WeaviateClientBase):
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
        self._event_loop = _EventLoopSingleton.get_instance()
        assert self._event_loop.loop is not None
        self._loop = self._event_loop.loop
        _EventLoop.patch_exception_handler(self._loop)

        super().__init__(
            connection_params=connection_params,
            embedded_options=embedded_options,
            auth_client_secret=auth_client_secret,
            additional_headers=additional_headers,
            additional_config=additional_config,
            skip_init_checks=skip_init_checks,
        )

        collections = _Collections(self._event_loop, _CollectionsAsync(self._connection))

        self.batch = _BatchClientWrapper(self._connection, config=collections)
        """This namespace contains all the functionality to upload data in batches to Weaviate for all collections and tenants."""
        self.backup = _Backup(self._connection)
        """This namespace contains all functionality to backup data."""
        self.cluster = _Cluster(self._connection)
        """This namespace contains all functionality to inspect the connected Weaviate cluster."""
        self.collections = collections
        """This namespace contains all the functionality to manage Weaviate data collections. It is your main entry point for all collection-related functionality.

        Use it to retrieve collection objects using `client.collections.get("MyCollection")` or to create new collections using `client.collections.create("MyCollection", ...)`.
        """

    def __enter__(self) -> "WeaviateClient":
        self.connect()  # pyright: ignore # gets patched by syncify.convert to be sync
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.close()  # pyright: ignore # gets patched by syncify.convert to be sync


class WeaviateAsyncClient(_WeaviateClientBase):
    """
    The v4 Python-native Weaviate Client class that encapsulates Weaviate functionalities in one object.

    WARNING: This client is only compatible with Weaviate v1.23.6 and higher!

    A Client instance creates all the needed objects to interact with Weaviate, and connects all of
    them to the same Weaviate instance. See below the Attributes of the Client instance. For the
    per attribute functionality see that attribute's documentation.

    Attributes:
        `backup`
            A `Backup` object instance connected to the same Weaviate instance as the Client.
        `cluster`
            A `Cluster` object instance connected to the same Weaviate instance as the Client.
        `collections`
            A `_CollectionsAsync` object instance connected to the same Weaviate instance as the Client.
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
        self._loop = asyncio.get_event_loop()
        _EventLoop.patch_exception_handler(self._loop)

        super().__init__(
            connection_params=connection_params,
            embedded_options=embedded_options,
            auth_client_secret=auth_client_secret,
            additional_headers=additional_headers,
            additional_config=additional_config,
            skip_init_checks=skip_init_checks,
        )

        self.backup = _BackupAsync(self._connection)
        """This namespace contains all functionality to backup data."""
        self.cluster = _ClusterAsync(self._connection)
        """This namespace contains all functionality to inspect the connected Weaviate cluster."""
        self.collections = _CollectionsAsync(self._connection)
        """This namespace contains all the functionality to manage Weaviate data collections. It is your main entry point for all collection-related functionality.

        Use it to retrieve collection objects using `client.collections.get("MyCollection")` or to create new collections using `await client.collections.create("MyCollection", ...)`.
        """

    async def __aenter__(self) -> "WeaviateAsyncClient":
        await self.connect()
        return self

    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        await self.close()


class Client:
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
