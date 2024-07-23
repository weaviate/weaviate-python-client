"""
Client class definition.
"""
import asyncio
from typing import Optional, Tuple, Union, Dict, Any

from httpx import HTTPError as HttpxError
from requests.exceptions import ConnectionError as RequestsConnectionError

from weaviate.backup.backup import _BackupAsync
from weaviate.backup.sync import _Backup
from weaviate.collections.classes.internal import _GQLEntryReturnType, _RawGQLReturn

from weaviate.integrations import _Integrations

from weaviate import syncify
from .auth import AuthCredentials
from .backup import Backup
from .batch import Batch
from .classification import Classification
from .cluster import Cluster
from weaviate.collections.collections.async_ import _CollectionsAsync
from weaviate.collections.collections.sync import _Collections
from .collections.batch.client import _BatchClientWrapper
from .collections.cluster import _Cluster, _ClusterAsync
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
from weaviate.event_loop import _EventLoopSingleton
from .types import NUMBER
from .util import _decode_json_response_dict, _get_valid_timeout_config, _type_request_response
from .validator import _validate_input, _ValidateArgument
from .warnings import _Warnings

TIMEOUT_TYPE = Union[Tuple[NUMBER, NUMBER], NUMBER]

from weaviate.client_base import _WeaviateClientInit

# Must define stubs here for WeaviateClient due to runtime patching of async -> sync methods
# Cannot move Client nor WeaviateClient definitions away from client.py due to BC concerns
# Must therefore duplicate the interface for all clients hiding their methods inside client.py

class WeaviateAsyncClient(_WeaviateClientInit):
    _connection: ConnectionV4
    collections: _CollectionsAsync
    backup: _BackupAsync
    cluster: _ClusterAsync
    async def close(self) -> None: ...
    async def connect(self) -> None: ...
    def is_connected(self) -> bool: ...
    async def is_live(self) -> bool: ...
    async def is_ready(self) -> bool: ...
    async def graphql_raw_query(self, gql_query: str) -> _RawGQLReturn: ...
    async def get_meta(self) -> dict: ...
    async def get_open_id_configuration(self) -> Optional[Dict[str, Any]]: ...
    async def __aenter__(self) -> "WeaviateAsyncClient": ...
    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None: ...

class WeaviateClient(_WeaviateClientInit):
    _connection: ConnectionV4
    collections: _Collections
    batch: _BatchClientWrapper
    backup: _Backup
    cluster: _Cluster
    def close(self) -> None: ...
    def connect(self) -> None: ...
    def is_connected(self) -> bool: ...
    def is_live(self) -> bool: ...
    def is_ready(self) -> bool: ...
    def graphql_raw_query(self, gql_query: str) -> _RawGQLReturn: ...
    def get_meta(self) -> dict: ...
    def get_open_id_configuration(self) -> Optional[Dict[str, Any]]: ...
    def __enter__(self) -> "WeaviateClient": ...
    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None: ...

class Client:
    _connection: Connection
    classification: Classification
    schema: Schema
    contextionary: Contextionary
    batch: Batch
    data_object: DataObject
    query: Query
    backup: Backup
    cluster: Cluster
    @property
    def timeout_config(self) -> TIMEOUT_TYPE_RETURN: ...
    def is_ready(self) -> bool: ...
    def is_live(self) -> bool: ...
    def get_meta(self) -> dict: ...
    def get_open_id_configuration(self) -> Optional[Dict[str, Any]]: ...
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
    ) -> None: ...
