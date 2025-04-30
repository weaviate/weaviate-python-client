from typing import List, Literal, Optional, Union, overload

from weaviate.cluster.types import Verbosity
from weaviate.collections.classes.cluster import Node, Shards, Stats
from weaviate.connect.v4 import ConnectionAsync

from .executor import _ClusterExecutor

class _ClusterAsync(_ClusterExecutor[ConnectionAsync]):
    @overload
    async def nodes(
        self, collection: Optional[str] = None, *, output: Literal[None] = None
    ) -> List[Node[None, None]]: ...
    @overload
    async def nodes(
        self, collection: Optional[str] = None, *, output: Literal["minimal"]
    ) -> List[Node[None, None]]: ...
    @overload
    async def nodes(
        self, collection: Optional[str] = None, *, output: Literal["verbose"]
    ) -> List[Node[Shards, Stats]]: ...
    @overload
    async def nodes(
        self, collection: Optional[str] = None, *, output: Optional[Verbosity] = None
    ) -> Union[List[Node[None, None]], List[Node[Shards, Stats]]]: ...
