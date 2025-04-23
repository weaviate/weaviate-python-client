from typing import Generic, List, Literal, Optional, Union, overload
from weaviate.collections.aggregations.base_executor import _BaseExecutor
from weaviate.collections.classes.aggregate import (
    PropertiesMetrics,
    AggregateReturn,
    AggregateGroupByReturn,
    GroupByAggregate,
)
from weaviate.collections.classes.filters import _Filters
from weaviate.collections.classes.grpc import Move
from weaviate.collections.filters import _FilterToGRPC
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionType
from weaviate.types import NUMBER
from weaviate.connect.v4 import ConnectionAsync
from .executor import _NearTextExecutor

class _NearTextAsync(_NearTextExecutor[ConnectionAsync]):
    @overload
    async def near_text(
        self,
        query: Union[List[str], str],
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
        return_metrics: Optional[PropertiesMetrics] = None
    ) -> AggregateReturn: ...
    @overload
    async def near_text(
        self,
        query: Union[List[str], str],
        *,
        certainty: Optional[NUMBER] = None,
        distance: Optional[NUMBER] = None,
        move_to: Optional[Move] = None,
        move_away: Optional[Move] = None,
        object_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Union[str, GroupByAggregate],
        target_vector: Optional[str] = None,
        total_count: bool = True,
        return_metrics: Optional[PropertiesMetrics] = None
    ) -> AggregateGroupByReturn: ...
    @overload
    async def near_text(
        self,
        query: Union[List[str], str],
        *,
        certainty: Optional[NUMBER] = None,
        distance: Optional[NUMBER] = None,
        move_to: Optional[Move] = None,
        move_away: Optional[Move] = None,
        object_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Optional[Union[str, GroupByAggregate]] = None,
        target_vector: Optional[str] = None,
        total_count: bool = True,
        return_metrics: Optional[PropertiesMetrics] = None
    ) -> Union[AggregateReturn, AggregateGroupByReturn]: ...
