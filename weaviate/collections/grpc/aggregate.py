from typing import List, Optional, cast

from grpc.aio import AioRpcError  # type: ignore

from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.grpc.retry import _Retry
from weaviate.collections.grpc.shared import _BaseGRPC, PERMISSION_DENIED
from weaviate.connect.v4 import ConnectionV4
from weaviate.exceptions import (
    InsufficientPermissionsError,
    WeaviateQueryError,
    WeaviateRetryError,
)
from weaviate.proto.v1 import aggregate_pb2, base_pb2


class _AggregateGRPC(_BaseGRPC):
    def __init__(
        self,
        connection: ConnectionV4,
        name: str,
        tenant: Optional[str],
        consistency_level: Optional[ConsistencyLevel],
        validate_arguments: bool,
    ):
        super().__init__(connection, consistency_level)
        self._name: str = name
        self._tenant = tenant
        self._validate_arguments = validate_arguments

    async def objects_count(self) -> int:
        res = await self.__call(self.__create_request(objects_count=True))
        return res.result.groups[0].objects_count

    async def over_all(
        self,
        *,
        aggregations: List[aggregate_pb2.AggregateRequest.Aggregation],
        filters: Optional[base_pb2.Filters],
        group_by: Optional[aggregate_pb2.AggregateRequest.GroupBy],
        objects_count: bool = False,
    ) -> aggregate_pb2.AggregateReply:
        return await self.__call(
            self.__create_request(
                aggregations=aggregations,
                filters=filters,
                group_by=group_by,
                objects_count=objects_count,
            )
        )

    def __create_request(
        self,
        *,
        aggregations: Optional[List[aggregate_pb2.AggregateRequest.Aggregation]] = None,
        filters: Optional[base_pb2.Filters] = None,
        group_by: Optional[aggregate_pb2.AggregateRequest.GroupBy] = None,
        objects_count: bool = False,
    ) -> aggregate_pb2.AggregateRequest:
        return aggregate_pb2.AggregateRequest(
            collection=self._name,
            aggregations=aggregations,
            filters=filters,
            group_by=group_by,
            objects_count=objects_count,
            tenant=self._tenant,
        )

    async def __call(self, request: aggregate_pb2.AggregateRequest) -> aggregate_pb2.AggregateReply:
        try:
            assert self._connection.grpc_stub is not None
            res = await _Retry(4).with_exponential_backoff(
                0,
                f"Searching in collection {request.collection}",
                self._connection.grpc_stub.Aggregate,
                request,
                metadata=self._connection.grpc_headers(),
                timeout=self._connection.timeout_config.query,
            )
            return cast(aggregate_pb2.AggregateReply, res)
        except AioRpcError as e:
            if e.code().name == PERMISSION_DENIED:
                raise InsufficientPermissionsError(e)
            raise WeaviateQueryError(str(e), "GRPC search")  # pyright: ignore
        except WeaviateRetryError as e:
            raise WeaviateQueryError(str(e), "GRPC search")  # pyright: ignore
