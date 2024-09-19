from typing import List, Literal, Optional, Union, overload

from weaviate.collections.aggregations.aggregate import _AggregateAsync
from weaviate.collections.classes.aggregate import (
    PropertiesMetrics,
    AggregateReturn,
    AggregateGroupByReturn,
    GroupByAggregate,
)
from weaviate.collections.classes.filters import _Filters
from weaviate.types import NUMBER

class _HybridAsync(_AggregateAsync):
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
        return_metrics: Optional[PropertiesMetrics] = None,
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
        return_metrics: Optional[PropertiesMetrics] = None,
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
        return_metrics: Optional[PropertiesMetrics] = None,
    ) -> Union[AggregateReturn, AggregateGroupByReturn]: ...

class _Hybrid(_AggregateAsync):
    @overload
    def hybrid(
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
        return_metrics: Optional[PropertiesMetrics] = None,
    ) -> AggregateReturn: ...
    @overload
    def hybrid(
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
        return_metrics: Optional[PropertiesMetrics] = None,
    ) -> AggregateGroupByReturn: ...
    @overload
    def hybrid(
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
        return_metrics: Optional[PropertiesMetrics] = None,
    ) -> Union[AggregateReturn, AggregateGroupByReturn]: ...
