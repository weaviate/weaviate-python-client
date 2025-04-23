from typing import Generic, Literal, Optional, Union, overload

from weaviate.collections.aggregations.base_executor import _BaseExecutor
from weaviate.collections.classes.aggregate import (
    PropertiesMetrics,
    AggregateReturn,
    AggregateGroupByReturn,
    GroupByAggregate,
)
from weaviate.collections.classes.filters import _Filters
from weaviate.collections.filters import _FilterToGRPC
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionType


class _OverAllExecutor(Generic[ConnectionType], _BaseExecutor[ConnectionType]):
    @overload
    def over_all(
        self,
        *,
        filters: Optional[_Filters] = None,
        group_by: Literal[None] = None,
        total_count: bool = True,
        return_metrics: Optional[PropertiesMetrics] = None,
    ) -> executor.Result[AggregateReturn]: ...

    @overload
    def over_all(
        self,
        *,
        filters: Optional[_Filters] = None,
        group_by: Union[str, GroupByAggregate],
        total_count: bool = True,
        return_metrics: Optional[PropertiesMetrics] = None,
    ) -> executor.Result[AggregateGroupByReturn]: ...

    @overload
    def over_all(
        self,
        *,
        filters: Optional[_Filters] = None,
        group_by: Optional[Union[str, GroupByAggregate]] = None,
        total_count: bool = True,
        return_metrics: Optional[PropertiesMetrics] = None,
    ) -> executor.Result[Union[AggregateReturn, AggregateGroupByReturn]]: ...

    def over_all(
        self,
        *,
        filters: Optional[_Filters] = None,
        group_by: Optional[Union[str, GroupByAggregate]] = None,
        total_count: bool = True,
        return_metrics: Optional[PropertiesMetrics] = None,
    ) -> executor.Result[Union[AggregateReturn, AggregateGroupByReturn]]:
        """Aggregate metrics over all the objects in this collection without any vector search.

        Args:
            filters: The filters to apply to the search.
            group_by: How to group the aggregation by.
            total_count: Whether to include the total number of objects that match the query in the response.
            return_metrics: A list of property metrics to aggregate together after the text search.

        Returns:
            Depending on the presence of the `group_by` argument, either a `AggregateReturn` object or a `AggregateGroupByReturn that includes the aggregation objects.

        Raises:
            weaviate.exceptions.WeaviateQueryError: If an error occurs while performing the query against Weaviate.
            weaviate.exceptions.WeaviateInvalidInputError: If any of the input arguments are of the wrong type.
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
            def resp(res: dict) -> Union[AggregateReturn, AggregateGroupByReturn]:
                return (
                    self._to_aggregate_result(res, return_metrics)
                    if group_by is None
                    else self._to_group_by_result(res, return_metrics)
                )

            builder = self._base(return_metrics, filters, total_count)
            builder = self._add_groupby_to_builder(builder, group_by)
            return executor.execute(
                response_callback=resp,
                method=self._do,
                query=builder,
            )

        else:
            # use grpc
            request = self._grpc.over_all(
                aggregations=(
                    [metric.to_grpc() for metric in return_metrics]
                    if return_metrics is not None
                    else []
                ),
                filters=_FilterToGRPC.convert(filters) if filters is not None else None,
                group_by=group_by._to_grpc() if group_by is not None else None,
                limit=group_by.limit if group_by is not None else None,
                objects_count=total_count,
            )
            return executor.execute(
                response_callback=self._to_result,
                method=self._connection.grpc_aggregate,
                request=request,
            )
