from typing import Literal, Optional, overload

from weaviate.cluster.models import (
    ReplicateOperationWithHistory,
    ReplicateOperationWithoutHistory,
)
from weaviate.connect.v4 import ConnectionAsync
from weaviate.types import UUID

from .executor import _ReplicateExecutor

class _ReplicateAsync(_ReplicateExecutor[ConnectionAsync]):
    @overload
    async def get(
        self, *, uuid: UUID, include_history: Literal[False] = False
    ) -> Optional[ReplicateOperationWithoutHistory]: ...
    @overload
    async def get(
        self, *, uuid: UUID, include_history: Literal[True]
    ) -> Optional[ReplicateOperationWithHistory]: ...
    async def list_all(self) -> list[ReplicateOperationWithHistory]: ...
    @overload
    async def query(
        self,
        *,
        collection: Optional[str] = None,
        shard: Optional[str] = None,
        target_node: Optional[str] = None,
        include_history: Literal[True],
    ) -> list[ReplicateOperationWithHistory]: ...
    @overload
    async def query(
        self,
        *,
        collection: Optional[str] = None,
        shard: Optional[str] = None,
        target_node: Optional[str] = None,
        include_history: Literal[False] = False,
    ) -> list[ReplicateOperationWithoutHistory]: ...
    async def cancel(self, *, uuid: UUID) -> None: ...
    async def delete(self, *, uuid: UUID) -> None: ...
    async def delete_all(self) -> None: ...
