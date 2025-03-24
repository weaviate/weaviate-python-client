from typing import Optional, Union

from weaviate import syncify
from weaviate.collections.aggregations.base import _BaseAggregate
from weaviate.collections.classes.aggregate import (
    PropertiesMetrics,
    AggregateReturn,
    AggregateGroupByReturn,
    GroupByAggregate,
)
from weaviate.collections.classes.filters import _Filters
from weaviate.connect.executor import aresult
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync
from weaviate.types import NUMBER, UUID


class _NearObjectAsync(_BaseAggregate[ConnectionAsync]):
    async def near_object(
        self,
        near_object: UUID,
        *,
        certainty: Optional[NUMBER] = None,
        distance: Optional[NUMBER] = None,
        object_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Optional[Union[str, GroupByAggregate]] = None,
        target_vector: Optional[str] = None,
        total_count: bool = True,
        return_metrics: Optional[PropertiesMetrics] = None,
    ) -> Union[AggregateReturn, AggregateGroupByReturn]:
        """Aggregate metrics over the objects returned by a near object search on this collection.

        At least one of `certainty`, `distance`, or `object_limit` must be specified here for the vector search.

        This method requires that the objects in the collection have associated vectors.

        Arguments:
            `near_object`
                The UUID of the object to search on.
            `certainty`
                The minimum certainty of the object search.
            `distance`
                The maximum distance of the object search.
            `object_limit`
                The maximum number of objects to return from the object search prior to the aggregation.
            `filters`
                The filters to apply to the search.
            `group_by`
                How to group the aggregation by.
            `total_count`
                Whether to include the total number of objects that match the query in the response.
            `return_metrics`
                A list of property metrics to aggregate together after the text search.

        Returns:
            Depending on the presence of the `group_by` argument, either a `AggregateReturn` object or a `AggregateGroupByReturn that includes the aggregation objects.

        Raises:
            `weaviate.exceptions.WeaviateQueryError`:
                If an error occurs while performing the query against Weaviate.
            `weaviate.exceptions.WeaviateInvalidInputError`:
                If any of the input arguments are of the wrong type.
        """
        return await aresult(
            self._executor.near_object(
                connection=self._connection,
                near_object=near_object,
                certainty=certainty,
                distance=distance,
                object_limit=object_limit,
                filters=filters,
                group_by=group_by,
                target_vector=target_vector,
                total_count=total_count,
                return_metrics=return_metrics,
            )
        )


@syncify.convert(_NearObjectAsync)
class _NearObject(_BaseAggregate[ConnectionSync]):
    pass
