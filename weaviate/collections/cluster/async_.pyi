from typing import List, Literal, Optional, Union, overload

from weaviate.cluster.types import Verbosity
from weaviate.collections.classes.cluster import NodeMinimal, NodeVerbose
from weaviate.connect.v4 import ConnectionAsync

from .executor import _ClusterExecutor

class _ClusterAsync(_ClusterExecutor[ConnectionAsync]):
    @overload
    async def nodes(
        self,
        collection: Optional[str] = None,
        shard: Optional[str] = None,
        *,
        output: Literal[None] = None,
    ) -> List[NodeMinimal]: ...
    @overload
    async def nodes(
        self,
        collection: Optional[str] = None,
        shard: Optional[str] = None,
        *,
        output: Literal["minimal"],
    ) -> List[NodeMinimal]: ...
    @overload
    async def nodes(
        self,
        collection: Optional[str] = None,
        shard: Optional[str] = None,
        *,
        output: Literal["verbose"],
    ) -> List[NodeVerbose]: ...
    @overload
    async def nodes(
        self,
        collection: Optional[str] = None,
        shard: Optional[str] = None,
        *,
        output: Optional[Verbosity] = None,
    ) -> Union[List[NodeMinimal], List[NodeVerbose]]: ...
