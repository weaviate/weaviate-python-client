"""
Client class definition.
"""

from typing import Optional, Tuple, Union, Dict, Any

from weaviate.backup.backup import _BackupAsync
from weaviate.backup.sync import _Backup
from weaviate.collections.classes.internal import _RawGQLReturn
from weaviate.collections.collections.async_ import _CollectionsAsync
from weaviate.collections.collections.sync import _Collections

from weaviate.users.users import _UsersAsync

from weaviate.users.sync import _Users
from .collections.batch.client import _BatchClientWrapper
from .collections.cluster import _Cluster, _ClusterAsync
from .connect import ConnectionV4
from .debug import _Debug, _DebugAsync
from .rbac import _Roles, _RolesAsync
from .types import NUMBER

TIMEOUT_TYPE = Union[Tuple[NUMBER, NUMBER], NUMBER]

from weaviate.client_base import _WeaviateClientInit

# Must define stubs here for WeaviateClient due to runtime patching of async -> sync methods
# Cannot move Client nor WeaviateClient definitions away from client.py due to BC concerns
# Must therefore duplicate the interface for all clients hiding their methods inside client.py

class WeaviateAsyncClient(_WeaviateClientInit):
    _connection: ConnectionV4
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

class WeaviateClient(_WeaviateClientInit):
    _connection: ConnectionV4
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
