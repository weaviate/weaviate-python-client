from typing import List, Optional, Union, cast

from weaviate import syncify
from weaviate.collections.aggregations.aggregate import _AggregateAsync
from weaviate.collections.classes.aggregate import (
    PropertiesMetrics,
    AggregateReturn,
    AggregateGroupByReturn,
    GroupByAggregate,
)
from weaviate.collections.classes.filters import _Filters
from weaviate.collections.classes.grpc import (
    TargetVectorJoinType,
    NearVectorInputType,
)
from weaviate.collections.filters import _FilterToGRPC
from weaviate.exceptions import WeaviateInvalidInputError
from weaviate.types import NUMBER


class _NearVectorAsync(_AggregateAsync):
    async def near_vector(
        self,
        near_vector: NearVectorInputType,
        *,
        certainty: Optional[NUMBER] = None,
        distance: Optional[NUMBER] = None,
        object_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Optional[Union[str, GroupByAggregate]] = None,
        target_vector: Optional[TargetVectorJoinType] = None,
        total_count: bool = True,
        return_metrics: Optional[PropertiesMetrics] = None,
    ) -> Union[AggregateReturn, AggregateGroupByReturn]:
        """Aggregate metrics over the objects returned by a near vector search on this collection.

        At least one of `certainty`, `distance`, or `object_limit` must be specified here for the vector search.

        This method requires that the objects in the collection have associated vectors.

        Arguments:
            `near_vector`
                The vector to search on.
            `certainty`
                The minimum certainty of the vector search.
            `distance`
                The maximum distance of the vector search.
            `object_limit`
                The maximum number of objects to return from the vector search prior to the aggregation.
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
        return_metrics = (
            return_metrics
            if (return_metrics is None or isinstance(return_metrics, list))
            else [return_metrics]
        )
        if isinstance(group_by, str):
            group_by = GroupByAggregate(prop=group_by)

        if self._connection._weaviate_version.is_lower_than(1, 29, 0):
            # use gql, remove once 1.29 is the minimum supported version

            if not isinstance(near_vector, list):
                raise WeaviateInvalidInputError(
                    "A `near_vector` argument other than a list of float is not supported in <v1.28.4",
                )
            if isinstance(near_vector[0], list):
                raise WeaviateInvalidInputError(
                    "A `near_vector` argument other than a list of floats is not supported in <v1.28.4",
                )
            near_vector = cast(
                List[float], near_vector
            )  # pylance cannot type narrow the immediately above check
            if target_vector is not None and not isinstance(target_vector, str):
                raise WeaviateInvalidInputError(
                    "A `target_vector` argument other than a string is not supported in <v1.28.4",
                )

            builder = self._base(return_metrics, filters, total_count)
            builder = self._add_groupby_to_builder(builder, group_by)
            builder = self._add_near_vector_to_builder(
                builder, near_vector, certainty, distance, object_limit, target_vector
            )
            res = await self._do(builder)
            return (
                self._to_aggregate_result(res, return_metrics)
                if group_by is None
                else self._to_group_by_result(res, return_metrics)
            )
        else:
            # use grpc
            reply = await self._grpc.near_vector(
                near_vector=near_vector,
                certainty=certainty,
                distance=distance,
                target_vector=target_vector,
                aggregations=(
                    [metric.to_grpc() for metric in return_metrics]
                    if return_metrics is not None
                    else []
                ),
                filters=_FilterToGRPC.convert(filters) if filters is not None else None,
                group_by=group_by._to_grpc() if group_by is not None else None,
                limit=group_by.limit if group_by is not None else None,
                objects_count=total_count,
                object_limit=object_limit,
            )
            return self._to_result(reply)


@syncify.convert
class _NearVector(_NearVectorAsync):
    pass
