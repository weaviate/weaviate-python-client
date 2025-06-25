from typing import Literal, Optional, Union, overload

from weaviate.collections.classes.aggregate import (
    AggregateGroupByReturn,
    AggregateReturn,
    GroupByAggregate,
    PropertiesMetrics,
)
from weaviate.collections.classes.filters import _Filters
from weaviate.connect.v4 import ConnectionAsync

from .executor import _OverAllExecutor

class _OverAllAsync(_OverAllExecutor[ConnectionAsync]):
    @overload
    async def over_all(
        self,
        *,
        filters: Optional[_Filters] = None,
        group_by: Literal[None] = None,
        total_count: bool = True,
        return_metrics: Optional[PropertiesMetrics] = None,
    ) -> AggregateReturn: ...
    @overload
    async def over_all(
        self,
        *,
        filters: Optional[_Filters] = None,
        group_by: Union[str, GroupByAggregate],
        total_count: bool = True,
        return_metrics: Optional[PropertiesMetrics] = None,
    ) -> AggregateGroupByReturn: ...
    @overload
    async def over_all(
        self,
        *,
        filters: Optional[_Filters] = None,
        group_by: Optional[Union[str, GroupByAggregate]] = None,
        total_count: bool = True,
        return_metrics: Optional[PropertiesMetrics] = None,
    ) -> Union[AggregateReturn, AggregateGroupByReturn]: ...
