from io import BufferedReader
from pathlib import Path
from typing import Optional, Union

from weaviate import syncify
from weaviate.collections.aggregations.aggregate import _AggregateAsync
from weaviate.collections.classes.aggregate import (
    PropertiesMetrics,
    AggregateReturn,
    AggregateGroupByReturn,
    GroupByAggregate,
)
from weaviate.collections.classes.filters import _Filters
from weaviate.types import NUMBER


class _NearImageAsync(_AggregateAsync):
    async def near_image(
        self,
        near_image: Union[str, Path, BufferedReader],
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
        """Aggregate metrics over the objects returned by a near image vector search on this collection.

        At least one of `certainty`, `distance`, or `object_limit` must be specified here for the vector search.

        This method requires a vectorizer capable of handling base64-encoded images, e.g. `img2vec-neural`, `multi2vec-clip`, and `multi2vec-bind`.

        Arguments:
            `near_image`
                The image to search on.
            `certainty`
                The minimum certainty of the image search.
            `distance`
                The maximum distance of the image search.
            `object_limit`
                The maximum number of objects to return from the image search prior to the aggregation.
            `filters`
                The filters to apply to the search.
            `group_by`
                The property name to group the aggregation by.
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
        builder = self._base(return_metrics, filters, total_count)
        builder = self._add_groupby_to_builder(builder, group_by)
        builder = self._add_near_image_to_builder(
            builder, near_image, certainty, distance, object_limit, target_vector
        )
        res = await self._do(builder)
        return (
            self._to_aggregate_result(res, return_metrics)
            if group_by is None
            else self._to_group_by_result(res, return_metrics)
        )


@syncify.convert
class _NearImage(_NearImageAsync):
    pass
