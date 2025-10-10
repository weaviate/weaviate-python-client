from typing import Literal, Optional, overload

from weaviate.collections.classes.aggregate import (
    AggregateGroupByReturn,
    AggregateReturn,
    GroupByAggregate,
    PropertiesMetrics,
)
from weaviate.collections.classes.filters import _Filters
from weaviate.collections.classes.grpc import Move
from weaviate.connect.v4 import ConnectionSync
from weaviate.types import NUMBER

from .executor import _NearTextExecutor

class _NearText(_NearTextExecutor[ConnectionSync]):
    @overload
    def near_text(
        self,
        query: list[str] | str,
        *,
        certainty: Optional[NUMBER] = None,
        distance: Optional[NUMBER] = None,
        move_to: Optional[Move] = None,
        move_away: Optional[Move] = None,
        object_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Literal[None] = None,
        target_vector: Optional[str] = None,
        total_count: bool = True,
        return_metrics: Optional[PropertiesMetrics] = None,
    ) -> AggregateReturn: ...
    @overload
    def near_text(
        self,
        query: list[str] | str,
        *,
        certainty: Optional[NUMBER] = None,
        distance: Optional[NUMBER] = None,
        move_to: Optional[Move] = None,
        move_away: Optional[Move] = None,
        object_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: str | GroupByAggregate,
        target_vector: Optional[str] = None,
        total_count: bool = True,
        return_metrics: Optional[PropertiesMetrics] = None,
    ) -> AggregateGroupByReturn: ...
    @overload
    def near_text(
        self,
        query: list[str] | str,
        *,
        certainty: Optional[NUMBER] = None,
        distance: Optional[NUMBER] = None,
        move_to: Optional[Move] = None,
        move_away: Optional[Move] = None,
        object_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Optional[str | GroupByAggregate] = None,
        target_vector: Optional[str] = None,
        total_count: bool = True,
        return_metrics: Optional[PropertiesMetrics] = None,
    ) -> AggregateReturn | AggregateGroupByReturn: ...
