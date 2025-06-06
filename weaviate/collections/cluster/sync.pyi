from typing import List, Literal, Optional, Union, overload

from weaviate.cluster.types import Verbosity
from weaviate.collections.classes.cluster import NodeMinimal, NodeVerbose
from weaviate.connect.v4 import ConnectionSync

from .executor import _ClusterExecutor

class _Cluster(_ClusterExecutor[ConnectionSync]):
    @overload
    def nodes(
        self,
        collection: Optional[str] = None,
        shard: Optional[str] = None,
        *,
        output: Literal[None] = None,
    ) -> List[NodeMinimal]: ...
    @overload
    def nodes(
        self,
        collection: Optional[str] = None,
        shard: Optional[str] = None,
        *,
        output: Literal["minimal"],
    ) -> List[NodeMinimal]: ...
    @overload
    def nodes(
        self,
        collection: Optional[str] = None,
        shard: Optional[str] = None,
        *,
        output: Literal["verbose"],
    ) -> List[NodeVerbose]: ...
    @overload
    def nodes(
        self,
        collection: Optional[str] = None,
        shard: Optional[str] = None,
        *,
        output: Optional[Verbosity] = None,
    ) -> Union[List[NodeMinimal], List[NodeVerbose]]: ...
