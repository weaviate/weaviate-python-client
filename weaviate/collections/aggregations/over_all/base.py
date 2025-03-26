from abc import abstractmethod
from typing import Generic, Optional, Union

from weaviate.collections.aggregations.base import _BaseAggregate
from weaviate.collections.classes.aggregate import (
    PropertiesMetrics,
    AggregateReturn,
    AggregateGroupByReturn,
    GroupByAggregate,
)
from weaviate.collections.classes.filters import _Filters
from weaviate.connect.executor import ExecutorResult
from weaviate.connect.v4 import ConnectionType


class _OverAllBase(Generic[ConnectionType], _BaseAggregate[ConnectionType]):
    @abstractmethod
    def over_all(
        self,
        *,
        filters: Optional[_Filters] = None,
        group_by: Optional[Union[str, GroupByAggregate]] = None,
        total_count: bool = True,
        return_metrics: Optional[PropertiesMetrics] = None,
    ) -> ExecutorResult[Union[AggregateReturn, AggregateGroupByReturn]]:
        """Aggregate metrics over all the objects in this collection without any vector search.

        Arguments:
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
