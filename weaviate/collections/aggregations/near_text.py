from typing import List, Optional, Union

from weaviate import syncify
from weaviate.collections.aggregations.aggregate import _AggregateAsync
from weaviate.collections.classes.aggregate import (
    PropertiesMetrics,
    AggregateReturn,
    AggregateGroupByReturn,
    GroupByAggregate,
)
from weaviate.collections.classes.filters import _Filters
from weaviate.collections.classes.grpc import Move
from weaviate.collections.filters import _FilterToGRPC
from weaviate.types import NUMBER


class _NearTextAsync(_AggregateAsync):
    async def near_text(
        self,
        query: Union[List[str], str],
        *,
        certainty: Optional[NUMBER] = None,
        distance: Optional[NUMBER] = None,
        move_to: Optional[Move] = None,
        move_away: Optional[Move] = None,
        object_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Optional[Union[str, GroupByAggregate]] = None,
        target_vector: Optional[str] = None,
        total_count: bool = True,
        return_metrics: Optional[PropertiesMetrics] = None,
    ) -> Union[AggregateReturn, AggregateGroupByReturn]:
        """Aggregate metrics over the objects returned by a near text vector search on this collection.

        At least one of `certainty`, `distance`, or `object_limit` must be specified here for the vector search.

        This method requires a vectorizer capable of handling text, e.g. `text2vec-contextionary`, `text2vec-openai`, etc.

        Arguments:
            `query`
                The text(s) to search on.
            `certainty`
                The minimum certainty of the text search.
            `distance`
                The maximum distance of the text search.
            `move_to`
                The vector to move the search towards.
            `move_away`
                The vector to move the search away from.
            `object_limit`
                The maximum number of objects to return from the text search prior to the aggregation.
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

            builder = self._base(return_metrics, filters, total_count)
            builder = self._add_groupby_to_builder(builder, group_by)
            builder = self._add_near_text_to_builder(
                builder=builder,
                query=query,
                certainty=certainty,
                distance=distance,
                move_to=move_to,
                move_away=move_away,
                object_limit=object_limit,
                target_vector=target_vector,
            )
            res = await self._do(builder)
            return (
                self._to_aggregate_result(res, return_metrics)
                if group_by is None
                else self._to_group_by_result(res, return_metrics)
            )
        else:
            # use grpc
            reply = await self._grpc.near_text(
                near_text=query,
                certainty=certainty,
                distance=distance,
                move_away=move_away,
                move_to=move_to,
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
class _NearText(_NearTextAsync):
    pass
