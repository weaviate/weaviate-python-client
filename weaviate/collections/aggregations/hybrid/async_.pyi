from typing import Generic, List, Literal, Optional, Union, overload
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
from weaviate.exceptions import WeaviateUnsupportedFeatureError
from weaviate.types import NUMBER
from weaviate.connect.v4 import ConnectionAsync
from .executor import _HybridExecutor

class _HybridAsync(_HybridExecutor[ConnectionAsync]):
    @overload
    async def hybrid(
        self,
        query: Optional[str],
        *,
        alpha: NUMBER = 0.7,
        vector: Optional[List[float]] = None,
        query_properties: Optional[List[str]] = None,
        object_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Literal[None] = None,
        target_vector: Optional[str] = None,
        max_vector_distance: Optional[float] = None,
        total_count: bool = True,
        return_metrics: Optional[PropertiesMetrics] = None
    ) -> AggregateReturn: ...
    @overload
    async def hybrid(
        self,
        query: Optional[str],
        *,
        alpha: NUMBER = 0.7,
        vector: Optional[List[float]] = None,
        query_properties: Optional[List[str]] = None,
        object_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Union[str, GroupByAggregate],
        target_vector: Optional[str] = None,
        max_vector_distance: Optional[float] = None,
        total_count: bool = True,
        return_metrics: Optional[PropertiesMetrics] = None
    ) -> AggregateGroupByReturn: ...
    @overload
    async def hybrid(
        self,
        query: Optional[str],
        *,
        alpha: NUMBER = 0.7,
        vector: Optional[List[float]] = None,
        query_properties: Optional[List[str]] = None,
        object_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Optional[Union[str, GroupByAggregate]] = None,
        target_vector: Optional[str] = None,
        max_vector_distance: Optional[float] = None,
        total_count: bool = True,
        return_metrics: Optional[PropertiesMetrics] = None
    ) -> Union[AggregateReturn, AggregateGroupByReturn]: ...
