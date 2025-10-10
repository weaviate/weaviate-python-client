from typing import Literal, Optional, overload

from weaviate.collections.classes.aggregate import (
    AggregateGroupByReturn,
    AggregateReturn,
    GroupByAggregate,
    PropertiesMetrics,
)
from weaviate.collections.classes.filters import _Filters
from weaviate.collections.classes.grpc import BM25OperatorOptions
from weaviate.connect.v4 import ConnectionSync
from weaviate.types import NUMBER

from .executor import _HybridExecutor

class _Hybrid(_HybridExecutor[ConnectionSync]):
    @overload
    def hybrid(
        self,
        query: Optional[str],
        *,
        alpha: NUMBER = 0.7,
        vector: Optional[list[float]] = None,
        query_properties: Optional[list[str]] = None,
        object_limit: Optional[int] = None,
        bm25_operator: Optional[BM25OperatorOptions] = None,
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
        vector: Optional[list[float]] = None,
        query_properties: Optional[list[str]] = None,
        object_limit: Optional[int] = None,
        bm25_operator: Optional[BM25OperatorOptions] = None,
        filters: Optional[_Filters] = None,
        group_by: str | GroupByAggregate,
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
        vector: Optional[list[float]] = None,
        query_properties: Optional[list[str]] = None,
        object_limit: Optional[int] = None,
        bm25_operator: Optional[BM25OperatorOptions] = None,
        filters: Optional[_Filters] = None,
        group_by: Optional[str | GroupByAggregate] = None,
        target_vector: Optional[str] = None,
        max_vector_distance: Optional[float] = None,
        total_count: bool = True,
        return_metrics: Optional[PropertiesMetrics] = None,
    ) -> AggregateReturn | AggregateGroupByReturn: ...
