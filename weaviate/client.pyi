"""
Client class definition.
"""

from typing import Any, Dict, Optional, Tuple, Union

from weaviate.aliases.async_ import _AliasAsync
from weaviate.aliases.sync import _Alias
from weaviate.client_executor import _WeaviateClientExecutor
from weaviate.collections.classes.internal import _RawGQLReturn
from weaviate.collections.collections.async_ import _CollectionsAsync
from weaviate.collections.collections.sync import _Collections
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync
from weaviate.users.async_ import _UsersAsync
from weaviate.users.sync import _Users

from .backup import _Backup, _BackupAsync
from .cluster import _Cluster, _ClusterAsync
from .collections.batch.client import _BatchClientWrapper
from .debug import _Debug, _DebugAsync
from .rbac import _Roles, _RolesAsync
from .types import NUMBER

TIMEOUT_TYPE = Union[Tuple[NUMBER, NUMBER], NUMBER]

class WeaviateAsyncClient(_WeaviateClientExecutor[ConnectionAsync]):
    _connection: ConnectionAsync
    alias: _AliasAsync
    backup: _BackupAsync
    collections: _CollectionsAsync
    cluster: _ClusterAsync
    debug: _DebugAsync
    roles: _RolesAsync
    users: _UsersAsync

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

class WeaviateClient(_WeaviateClientExecutor[ConnectionSync]):
    _connection: ConnectionSync
    alias: _Alias
    backup: _Backup
    batch: _BatchClientWrapper
    collections: _Collections
    cluster: _Cluster
    debug: _Debug
    roles: _Roles
    users: _Users

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
    def __init__(self) -> None: ...
