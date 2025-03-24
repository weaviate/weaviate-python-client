from typing import List, Optional, Union

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
from weaviate.types import NUMBER


class _HybridAsync(_BaseAggregate[ConnectionAsync]):
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
        max_vector_distance: Optional[NUMBER] = None,
        total_count: bool = True,
        return_metrics: Optional[PropertiesMetrics] = None,
    ) -> Union[AggregateReturn, AggregateGroupByReturn]:
        """Aggregate metrics over all the objects in this collection using the hybrid algorithm blending keyword-based BM25 and vector-based similarity.

        Arguments:
            `query`
                The keyword-based query to search for, REQUIRED. If query and vector are both None, a normal search will be performed.
            `alpha`
                The weight of the BM25 score. If not specified, the default weight specified by the server is used.
            `vector`
                The specific vector to search for. If not specified, the query is vectorized and used in the similarity search.
            `query_properties`
                The properties to search in. If not specified, all properties are searched.
            `object_limit`
                The maximum number of objects to return from the hybrid vector search prior to the aggregation.
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
            self._executor.hybrid(
                connection=self._connection,
                query=query,
                alpha=alpha,
                vector=vector,
                query_properties=query_properties,
                object_limit=object_limit,
                filters=filters,
                group_by=group_by,
                target_vector=target_vector,
                max_vector_distance=max_vector_distance,
                total_count=total_count,
                return_metrics=return_metrics,
            )
        )


@syncify.convert(_HybridAsync)
class _Hybrid(_BaseAggregate[ConnectionSync]):
    pass
