import uuid
from typing import List, Literal, Optional, Union, overload

from weaviate.cluster.models import ShardingState, TransferType
from weaviate.cluster.replicate import _ReplicateAsync
from weaviate.cluster.types import Verbosity
from weaviate.collections.classes.cluster import NodeMinimal, NodeVerbose
from weaviate.connect.v4 import ConnectionAsync

from .base import _ClusterExecutor

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
    async def replicate(
        self,
        *,
        collection: str,
        shard: str,
        source_node: str,
        target_node: str,
        transfer_type: TransferType = TransferType.COPY,
    ) -> uuid.UUID: ...
    async def query_sharding_state(
        self,
        *,
        collection: str,
        shard: Optional[str] = None,
    ) -> Optional[ShardingState]: ...
    @property
    def replications(self) -> _ReplicateAsync: ...
