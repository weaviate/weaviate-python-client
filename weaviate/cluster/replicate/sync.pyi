from typing import Literal, Optional, overload

from weaviate.cluster.models import (
    ReplicateOperationWithHistory,
    ReplicateOperationWithoutHistory,
    ReplicationScaleApplyResult,
    ReplicationScalePlan,
)
from weaviate.connect.v4 import ConnectionSync
from weaviate.types import UUID

from .executor import _ReplicateExecutor

class _Replicate(_ReplicateExecutor[ConnectionSync]):
    def generate_scale_plan(
        self, *, collection: str, replication_factor: int
    ) -> ReplicationScalePlan: ...
    def apply_scale_plan(self, *, plan: ReplicationScalePlan) -> ReplicationScaleApplyResult: ...
    @overload
    def get(
        self, *, uuid: UUID, include_history: Literal[False] = False
    ) -> Optional[ReplicateOperationWithoutHistory]: ...
    @overload
    def get(
        self, *, uuid: UUID, include_history: Literal[True]
    ) -> Optional[ReplicateOperationWithHistory]: ...
    def list_all(self) -> list[ReplicateOperationWithHistory]: ...
    @overload
    def query(
        self,
        *,
        collection: Optional[str] = None,
        shard: Optional[str] = None,
        target_node: Optional[str] = None,
        include_history: Literal[True],
    ) -> list[ReplicateOperationWithHistory]: ...
    @overload
    def query(
        self,
        *,
        collection: Optional[str] = None,
        shard: Optional[str] = None,
        target_node: Optional[str] = None,
        include_history: Literal[False] = False,
    ) -> list[ReplicateOperationWithoutHistory]: ...
    def cancel(self, *, uuid: UUID) -> None: ...
    def delete(self, *, uuid: UUID) -> None: ...
    def delete_all(self) -> None: ...
