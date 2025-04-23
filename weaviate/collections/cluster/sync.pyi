from typing import Generic, List, Literal, Optional, Union, overload
from httpx import Response
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionType
from weaviate.cluster.types import Verbosity
from weaviate.collections.classes.cluster import Node, Shards, _ConvertFromREST, Stats
from weaviate.exceptions import EmptyResponseError
from weaviate.util import _capitalize_first_letter, _decode_json_response_dict
from weaviate.connect.v4 import ConnectionSync
from .executor import _ClusterExecutor

class _Cluster(_ClusterExecutor[ConnectionSync]):
    @overload
    def nodes(
        self, collection: Optional[str] = None, *, output: Literal[None] = None
    ) -> List[Node[None, None]]: ...
    @overload
    def nodes(
        self, collection: Optional[str] = None, *, output: Literal["minimal"]
    ) -> List[Node[None, None]]: ...
    @overload
    def nodes(
        self, collection: Optional[str] = None, *, output: Literal["verbose"]
    ) -> List[Node[Shards, Stats]]: ...
    @overload
    def nodes(
        self, collection: Optional[str] = None, *, output: Optional[Verbosity] = None
    ) -> Union[List[Node[None, None]], List[Node[Shards, Stats]]]: ...
