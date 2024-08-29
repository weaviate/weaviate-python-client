from typing import List, Literal, Optional, overload

from weaviate.cluster.types import Node as NodeREST
from weaviate.collections.classes.cluster import Node, Shards, Stats
from weaviate.collections.cluster.cluster import _ClusterBase

class _Cluster(_ClusterBase):
    @overload
    def nodes(
        self,
        collection: Optional[str] = None,
        *,
        output: Literal[None] = None,
    ) -> List[Node[None, None]]: ...
    @overload
    def nodes(
        self,
        collection: Optional[str] = None,
        *,
        output: Literal["minimal"],
    ) -> List[Node[None, None]]: ...
    @overload
    def nodes(
        self,
        collection: Optional[str] = None,
        *,
        output: Literal["verbose"],
    ) -> List[Node[Shards, Stats]]: ...
    def rest_nodes(
        self,
        collection: Optional[str] = None,
        output: Optional[Literal["minimal", "verbose"]] = None,
    ) -> List[NodeREST]: ...
