from typing import List, Literal, Optional, overload

from weaviate.connect.v4 import ConnectionAsync
from weaviate.replication.models import ReplicateOperation, ReplicateOperationStatus
from weaviate.types import UUID

from .executor import _OperationsExecutor

class _OperationsAsync(_OperationsExecutor[ConnectionAsync]):
    @overload
    async def get(
        self, *, uuid: UUID, include_history: Literal[False] = False
    ) -> Optional[ReplicateOperation[None]]: ...
    @overload
    async def get(
        self, *, uuid: UUID, include_history: Literal[True]
    ) -> Optional[ReplicateOperation[List[ReplicateOperationStatus]]]: ...
    async def list_all(self) -> list[ReplicateOperation]: ...
    async def query(
        self,
        *,
        collection: Optional[str] = None,
        shard: Optional[str] = None,
        target_node: Optional[str] = None,
        include_history: bool = False,
    ) -> list[ReplicateOperation]: ...
    async def cancel(self, *, uuid: UUID) -> None: ...
    async def delete(self, *, uuid: UUID) -> None: ...
    async def delete_all(self) -> None: ...
