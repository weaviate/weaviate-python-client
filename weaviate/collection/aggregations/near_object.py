from typing import List, Optional

from weaviate.collection.aggregations.base import _Aggregate
from weaviate.collection.classes.aggregate import (
    MetricsQuery,
    _AggregateReturn,
    _AggregateGroupByReturn,
)
from weaviate.collection.classes.filters import _Filters
from weaviate.types import UUID


class _NearObject(_Aggregate):
    def near_object(
        self,
        near_object: UUID,
        metrics: MetricsQuery,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        object_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        limit: Optional[int] = None,
        total_count: bool = False,
    ) -> _AggregateReturn:
        """Aggregate metrics over the objects returned by a near object search on this collection.

        At least one of `certainty`, `distance`, or `object_limit` must be specified here for the vector search.

        This method requires that the objects in the collection have associated vectors.

        Arguments:
            `near_object`
                The UUID of the object to search on.
            `metrics`
                A list of metrics to aggregate after the object search.
            `certainty`
                The minimum certainty of the object search.
            `distance`
                The maximum distance of the object search.
            `object_limit`
                The maximum number of objects to return from the object search prior to the aggregation.
            `filters`
                The filters to apply to the search.
            `limit`
                The maximum number of aggregated objects to return.
            `total_count`
                Whether to include the total number of objects that match the query in the response.

        Returns:
            A `_AggregateReturn` object that includes the aggregation objects.

        Raises:
            `weaviate.exceptions.WeaviateQueryException`:
                If an error occurs while performing the query against Weaviate.
        """
        builder = self._base(metrics, filters, limit, total_count)
        builder = self._add_near_object(builder, near_object, certainty, distance, object_limit)
        res = self._do(builder)
        return self._to_aggregate_result(res, metrics)


class _NearObjectGroupBy(_Aggregate):
    def near_object(
        self,
        near_object: UUID,
        metrics: MetricsQuery,
        group_by: str,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        object_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        limit: Optional[int] = None,
        total_count: bool = False,
    ) -> List[_AggregateGroupByReturn]:
        """Aggregate metrics over the objects returned by a near object vector search on this collection grouping the results by a property.

        At least one of `certainty`, `distance`, or `object_limit` must be specified here for the vector search.

        This method requires that the objects in the collection have associated vectors.

        Arguments:
            `near_object`
                The UUID of the object to search on.
            `metrics`
                A list of metrics to aggregate after the object search.
            `group_by`
                The property name to group the aggregation by.
            `certainty`
                The minimum certainty of the object search.
            `distance`
                The maximum distance of the object search.
            `object_limit`
                The maximum number of objects to return from the object search prior to the aggregation.
            `filters`
                The filters to apply to the search.
            `limit`
                The maximum number of aggregated objects to return.
            `total_count`
                Whether to include the total number of objects that match the query in the response.

        Returns:
            A `_AggregateGroupByReturn` object that includes the aggregation objects.

        Raises:
            `weaviate.exceptions.WeaviateQueryException`:
                If an error occurs while performing the query against Weaviate.
        """
        builder = (
            self._base(metrics, filters, limit, total_count)
            .with_group_by_filter([group_by])
            .with_fields(" groupedBy { path value } ")
        )
        builder = self._add_near_object(builder, near_object, certainty, distance, object_limit)
        res = self._do(builder)
        return self._to_group_by_result(res, metrics)
