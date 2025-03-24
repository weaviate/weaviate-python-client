from typing import Optional, Union

from weaviate.collections.aggregations.executors.base import _BaseExecutor
from weaviate.collections.classes.aggregate import (
    PropertiesMetrics,
    AggregateReturn,
    AggregateGroupByReturn,
    GroupByAggregate,
)
from weaviate.collections.classes.filters import _Filters
from weaviate.collections.filters import _FilterToGRPC
from weaviate.connect.executor import execute, ExecutorResult
from weaviate.connect.v4 import Connection


class _OverAllExecutor(_BaseExecutor):
    def over_all(
        self,
        connection: Connection,
        *,
        filters: Optional[_Filters] = None,
        group_by: Optional[Union[str, GroupByAggregate]] = None,
        total_count: bool = True,
        return_metrics: Optional[PropertiesMetrics] = None,
    ) -> ExecutorResult[Union[AggregateReturn, AggregateGroupByReturn]]:
        return_metrics = (
            return_metrics
            if (return_metrics is None or isinstance(return_metrics, list))
            else [return_metrics]
        )
        if isinstance(group_by, str):
            group_by = GroupByAggregate(prop=group_by)

        if connection._weaviate_version.is_lower_than(1, 29, 0):
            # use gql, remove once 1.29 is the minimum supported version
            def resp(res: dict) -> Union[AggregateReturn, AggregateGroupByReturn]:
                return (
                    self._to_aggregate_result(res, return_metrics)
                    if group_by is None
                    else self._to_group_by_result(res, return_metrics)
                )

            builder = self._base(return_metrics, filters, total_count)
            builder = self._add_groupby_to_builder(builder, group_by)
            return execute(
                response_callback=resp,
                method=self._do,
                connection=connection,
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
            return execute(
                response_callback=self._to_result, method=connection.grpc_aggregate, request=request
            )
