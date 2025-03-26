from abc import abstractmethod
from typing import Generic, List, Optional, Union

from weaviate.collections.aggregations.base import _BaseAggregate
from weaviate.collections.classes.aggregate import (
    PropertiesMetrics,
    AggregateReturn,
    AggregateGroupByReturn,
    GroupByAggregate,
)
from weaviate.collections.classes.filters import _Filters
from weaviate.collections.classes.grpc import Move
from weaviate.connect.executor import ExecutorResult
from weaviate.connect.v4 import ConnectionType
from weaviate.types import NUMBER


class _NearTextBase(Generic[ConnectionType], _BaseAggregate[ConnectionType]):
    @abstractmethod
    def near_text(
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
    ) -> ExecutorResult[Union[AggregateReturn, AggregateGroupByReturn]]:
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
        raise NotImplementedError()
