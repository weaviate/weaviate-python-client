from typing import List, Literal, Optional, Union, overload

from weaviate.collections.classes.cluster import Node, Shards, Stats
from weaviate.collections.cluster.base import _ClusterBase
from weaviate.cluster.types import Verbosity
from weaviate.connect.v4 import ConnectionAsync

class _ClusterAsync(_ClusterBase[ConnectionAsync]):
    @overload
    async def nodes(
        self,
        collection: Optional[str] = None,
        *,
        output: Literal[None] = None,
    ) -> List[Node[None, None]]: ...
    @overload
    async def nodes(
        self,
        collection: Optional[str] = None,
        *,
        output: Literal["minimal"],
    ) -> List[Node[None, None]]: ...
    @overload
    async def nodes(
        self,
        collection: Optional[str] = None,
        *,
        output: Literal["verbose"],
    ) -> List[Node[Shards, Stats]]: ...
    @overload
    async def nodes(
        self,
        collection: Optional[str] = None,
        output: Optional[Verbosity] = None,
    ) -> Union[List[Node[None, None]], List[Node[Shards, Stats]]]: ...
