import uuid
from typing import Literal, Optional, overload

from weaviate.cluster.models import ReplicationType, ShardingState
from weaviate.cluster.replicate import _Replicate
from weaviate.cluster.types import Verbosity
from weaviate.collections.classes.cluster import NodeMinimal, NodeVerbose
from weaviate.connect.v4 import ConnectionSync

from .base import _ClusterExecutor

class _Cluster(_ClusterExecutor[ConnectionSync]):
    @overload
    def nodes(
        self,
        collection: Optional[str] = None,
        shard: Optional[str] = None,
        *,
        output: Literal[None] = None,
    ) -> list[NodeMinimal]: ...
    @overload
    def nodes(
        self,
        collection: Optional[str] = None,
        shard: Optional[str] = None,
        *,
        output: Literal["minimal"],
    ) -> list[NodeMinimal]: ...
    @overload
    def nodes(
        self,
        collection: Optional[str] = None,
        shard: Optional[str] = None,
        *,
        output: Literal["verbose"],
    ) -> list[NodeVerbose]: ...
    @overload
    def nodes(
        self,
        collection: Optional[str] = None,
        shard: Optional[str] = None,
        *,
        output: Optional[Verbosity] = None,
    ) -> list[NodeMinimal] | list[NodeVerbose]: ...
    def replicate(
        self,
        *,
        collection: str,
        shard: str,
        source_node: str,
        target_node: str,
        replication_type: ReplicationType = ReplicationType.COPY,
    ) -> uuid.UUID: ...
    def query_sharding_state(
        self,
        *,
        collection: str,
        shard: Optional[str] = None,
    ) -> Optional[ShardingState]: ...
    @property
    def replications(self) -> _Replicate:
        """replication (_Replication): Replication object instance connected to the same Weaviate instance as the Client.
        This namespace contains all functionality to manage replication operations in Weaviate."""
        ...
