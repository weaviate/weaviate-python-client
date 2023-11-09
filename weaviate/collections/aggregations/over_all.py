from typing import List, Optional

from weaviate.collections.aggregations.base import _Aggregate
from weaviate.collections.classes.aggregate import (
    PropertiesMetrics,
    _AggregateReturn,
    _AggregateGroupByReturn,
)
from weaviate.collections.classes.filters import _Filters


class _OverAll(_Aggregate):
    def over_all(
        self,
        filters: Optional[_Filters] = None,
        limit: Optional[int] = None,
        total_count: bool = True,
        return_metrics: Optional[PropertiesMetrics] = None,
    ) -> _AggregateReturn:
        """Aggregate metrics over all the objects in this collection without any vector search.

        Arguments:
            `filters`
                The filters to apply to the search.
            `limit`
                The maximum number of aggregated objects to return.
            `total_count`
                Whether to include the total number of objects that match the query in the response.
            `return_metrics`
                A list of property metrics to aggregate together after the text search.

        Returns:
            A `_AggregateReturn` object that includes the aggregation objects.

        Raises:
            `weaviate.exceptions.WeaviateQueryException`:
                If an error occurs while performing the query against Weaviate.
        """
        return_metrics = (
            return_metrics
            if (return_metrics is None or isinstance(return_metrics, list))
            else [return_metrics]
        )
        builder = self._base(return_metrics, filters, limit, total_count)
        res = self._do(builder)
        return self._to_aggregate_result(res, return_metrics)


class _OverAllGroupBy(_Aggregate):
    def over_all(
        self,
        group_by: str,
        filters: Optional[_Filters] = None,
        limit: Optional[int] = None,
        total_count: bool = True,
        return_metrics: Optional[PropertiesMetrics] = None,
    ) -> List[_AggregateGroupByReturn]:
        """Aggregate metrics over all the objects in this collection without any vector search grouping the results by a property.

        Arguments:
            `group_by`
                The property name to group the aggregation by.
            `filters`
                The filters to apply to the search.
            `limit`
                The maximum number of aggregated objects to return.
            `total_count`
                Whether to include the total number of objects that match the query in the response.
            `return_metrics`
                A list of property metrics to aggregate together after the text search.

        Returns:
            A `_AggregateGroupByReturn` object that includes the aggregation objects.

        Raises:
            `weaviate.exceptions.WeaviateQueryException`:
                If an error occurs while performing the query against Weaviate.
        """
        return_metrics = (
            return_metrics
            if (return_metrics is None or isinstance(return_metrics, list))
            else [return_metrics]
        )
        builder = (
            self._base(return_metrics, filters, limit, total_count)
            .with_group_by_filter([group_by])
            .with_fields(" groupedBy { path value } ")
        )
        res = self._do(builder)
        return self._to_group_by_result(res, return_metrics)
