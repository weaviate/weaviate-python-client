from typing import List, Literal, Optional, overload

from weaviate.connect.v4 import ConnectionSync
from weaviate.replication.models import ReplicateOperation, ReplicateOperationStatus
from weaviate.types import UUID

from .executor import _OperationsExecutor

class _Operations(_OperationsExecutor[ConnectionSync]):
    @overload
    def get(
        self, *, uuid: UUID, include_history: Literal[False] = False
    ) -> Optional[ReplicateOperation[None]]: ...
    @overload
    def get(
        self, *, uuid: UUID, include_history: Literal[True]
    ) -> Optional[ReplicateOperation[List[ReplicateOperationStatus]]]: ...
    def list_all(self) -> list[ReplicateOperation]: ...
    def query(
        self,
        *,
        collection: Optional[str] = None,
        shard: Optional[str] = None,
        target_node: Optional[str] = None,
        include_history: bool = False,
    ) -> list[ReplicateOperation]: ...
    def cancel(self, *, uuid: UUID) -> None: ...
    def delete(self, *, uuid: UUID) -> None: ...
    def delete_all(self) -> None: ...
