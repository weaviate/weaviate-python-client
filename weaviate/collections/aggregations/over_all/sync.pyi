from typing import Generic, Literal, Optional, Union, overload
from weaviate.collections.aggregations.base_executor import _BaseExecutor
from weaviate.collections.classes.aggregate import (
    PropertiesMetrics,
    AggregateReturn,
    AggregateGroupByReturn,
    GroupByAggregate,
)
from weaviate.collections.classes.filters import _Filters
from weaviate.collections.filters import _FilterToGRPC
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionType
from weaviate.connect.v4 import ConnectionSync
from .executor import _OverAllExecutor

class _OverAll(_OverAllExecutor[ConnectionSync]):
    @overload
    def over_all(
        self,
        *,
        filters: Optional[_Filters] = None,
        group_by: Literal[None] = None,
        total_count: bool = True,
        return_metrics: Optional[PropertiesMetrics] = None
    ) -> AggregateReturn: ...
    @overload
    def over_all(
        self,
        *,
        filters: Optional[_Filters] = None,
        group_by: Union[str, GroupByAggregate],
        total_count: bool = True,
        return_metrics: Optional[PropertiesMetrics] = None
    ) -> AggregateGroupByReturn: ...
    @overload
    def over_all(
        self,
        *,
        filters: Optional[_Filters] = None,
        group_by: Optional[Union[str, GroupByAggregate]] = None,
        total_count: bool = True,
        return_metrics: Optional[PropertiesMetrics] = None
    ) -> Union[AggregateReturn, AggregateGroupByReturn]: ...
