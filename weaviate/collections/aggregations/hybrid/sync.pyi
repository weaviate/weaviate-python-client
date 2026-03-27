from typing import List, Literal, Optional, Union, overload

from weaviate.collections.classes.aggregate import (
    AggregateGroupByReturn,
    AggregateReturn,
    GroupByAggregate,
    PropertiesMetrics,
)
from weaviate.collections.classes.filters import FilterReturn
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
        alpha: Optional[NUMBER] = None,
        vector: Optional[List[float]] = None,
        query_properties: Optional[List[str]] = None,
        object_limit: Optional[int] = None,
        bm25_operator: Optional[BM25OperatorOptions] = None,
        filters: Optional[FilterReturn] = None,
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
        alpha: Optional[NUMBER] = None,
        vector: Optional[List[float]] = None,
        query_properties: Optional[List[str]] = None,
        object_limit: Optional[int] = None,
        bm25_operator: Optional[BM25OperatorOptions] = None,
        filters: Optional[FilterReturn] = None,
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
        alpha: Optional[NUMBER] = None,
        vector: Optional[List[float]] = None,
        query_properties: Optional[List[str]] = None,
        object_limit: Optional[int] = None,
        bm25_operator: Optional[BM25OperatorOptions] = None,
        filters: Optional[FilterReturn] = None,
        group_by: Optional[Union[str, GroupByAggregate]] = None,
        target_vector: Optional[str] = None,
        max_vector_distance: Optional[float] = None,
        total_count: bool = True,
        return_metrics: Optional[PropertiesMetrics] = None,
    ) -> Union[AggregateReturn, AggregateGroupByReturn]: ...
