from typing import List, Optional, Union

from weaviate.collections.aggregations.executors.base import _BaseExecutor
from weaviate.collections.classes.aggregate import (
    PropertiesMetrics,
    AggregateReturn,
    AggregateGroupByReturn,
    GroupByAggregate,
)
from weaviate.collections.classes.filters import _Filters
from weaviate.collections.classes.grpc import Move
from weaviate.collections.filters import _FilterToGRPC
from weaviate.connect.executor import execute, ExecutorResult
from weaviate.connect.v4 import Connection
from weaviate.types import NUMBER


class _NearTextExecutor(_BaseExecutor):
    def near_text(
        self,
        connection: Connection,
        *,
        query: Union[List[str], str],
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
            return execute(
                response_callback=resp,
                method=self._do,
                connection=connection,
                query=builder,
            )
        else:
            # use grpc
            request = self._grpc.near_text(
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
            return execute(
                response_callback=self._to_result, method=connection.grpc_aggregate, request=request
            )
