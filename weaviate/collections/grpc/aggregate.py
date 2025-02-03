from typing import Awaitable, List, Literal, Optional, Union, cast

from grpc.aio import AioRpcError  # type: ignore

from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.grpc import (
    TargetVectorJoinType,
    NearVectorInputType,
    Move,
    HybridVectorType,
)
from weaviate.collections.grpc.retry import _Retry
from weaviate.collections.grpc.shared import _BaseGRPC, PERMISSION_DENIED
from weaviate.connect.v4 import ConnectionV4
from weaviate.exceptions import (
    InsufficientPermissionsError,
    WeaviateQueryError,
    WeaviateRetryError,
    WeaviateInvalidInputError,
)
from weaviate.proto.v1 import aggregate_pb2, base_pb2, base_search_pb2
from weaviate.types import NUMBER, UUID


class _AggregateGRPC(_BaseGRPC):
    def __init__(
        self,
        connection: ConnectionV4,
        name: str,
        tenant: Optional[str],
        consistency_level: Optional[ConsistencyLevel],
        validate_arguments: bool,
    ):
        super().__init__(connection, consistency_level, validate_arguments)
        self._name: str = name
        self._tenant = tenant

    async def objects_count(self) -> int:
        res = await self.__call(self.__create_request(objects_count=True))
        return res.single_result.objects_count

    def hybrid(
        self,
        *,
        query: Optional[str],
        alpha: Optional[float],
        vector: Optional[HybridVectorType],
        properties: Optional[List[str]],
        distance: Optional[NUMBER] = None,
        target_vector: Optional[TargetVectorJoinType],
        aggregations: List[aggregate_pb2.AggregateRequest.Aggregation],
        filters: Optional[base_pb2.Filters],
        group_by: Optional[aggregate_pb2.AggregateRequest.GroupBy],
        limit: Optional[int],
        object_limit: Optional[int],
        objects_count: bool,
    ) -> Awaitable[aggregate_pb2.AggregateReply]:
        request = self.__create_request(
            aggregations=aggregations,
            filters=filters,
            group_by=group_by,
            hybrid=self._parse_hybrid(
                query,
                alpha,
                vector,
                properties,
                None,
                distance,
                target_vector,
            ),
            limit=limit,
            object_limit=object_limit,
            objects_count=objects_count,
        )
        return self.__call(request)

    def near_media(
        self,
        *,
        media: str,
        type_: Literal["audio", "depth", "image", "imu", "thermal", "video"],
        certainty: Optional[NUMBER] = None,
        distance: Optional[NUMBER] = None,
        target_vector: Optional[TargetVectorJoinType],
        aggregations: List[aggregate_pb2.AggregateRequest.Aggregation],
        filters: Optional[base_pb2.Filters],
        group_by: Optional[aggregate_pb2.AggregateRequest.GroupBy],
        limit: Optional[int],
        object_limit: Optional[int],
        objects_count: bool,
    ) -> Awaitable[aggregate_pb2.AggregateReply]:
        if self._validate_arguments:
            self.__check_vector_search_args(
                certainty=certainty,
                distance=distance,
                object_limit=object_limit,
            )
        request = self.__create_request(
            aggregations=aggregations,
            filters=filters,
            group_by=group_by,
            limit=limit,
            **self._parse_media(
                media,
                type_,
                certainty,
                distance,
                target_vector,
            ),
            object_limit=object_limit,
            objects_count=objects_count,
        )
        return self.__call(request)

    def near_object(
        self,
        *,
        near_object: UUID,
        certainty: Optional[NUMBER] = None,
        distance: Optional[NUMBER] = None,
        target_vector: Optional[TargetVectorJoinType],
        aggregations: List[aggregate_pb2.AggregateRequest.Aggregation],
        filters: Optional[base_pb2.Filters],
        group_by: Optional[aggregate_pb2.AggregateRequest.GroupBy],
        limit: Optional[int],
        object_limit: Optional[int],
        objects_count: bool,
    ) -> Awaitable[aggregate_pb2.AggregateReply]:
        if self._validate_arguments:
            self.__check_vector_search_args(
                certainty=certainty,
                distance=distance,
                object_limit=object_limit,
            )
        request = self.__create_request(
            aggregations=aggregations,
            filters=filters,
            group_by=group_by,
            limit=limit,
            near_object=self._parse_near_object(near_object, certainty, distance, target_vector),
            object_limit=object_limit,
            objects_count=objects_count,
        )
        return self.__call(request)

    def near_text(
        self,
        *,
        near_text: Union[List[str], str],
        certainty: Optional[NUMBER],
        distance: Optional[NUMBER],
        move_to: Optional[Move],
        move_away: Optional[Move],
        target_vector: Optional[TargetVectorJoinType],
        aggregations: List[aggregate_pb2.AggregateRequest.Aggregation],
        filters: Optional[base_pb2.Filters],
        group_by: Optional[aggregate_pb2.AggregateRequest.GroupBy],
        limit: Optional[int],
        object_limit: Optional[int],
        objects_count: bool,
    ) -> Awaitable[aggregate_pb2.AggregateReply]:
        if self._validate_arguments:
            self.__check_vector_search_args(
                certainty=certainty,
                distance=distance,
                object_limit=object_limit,
            )
        request = self.__create_request(
            aggregations=aggregations,
            filters=filters,
            group_by=group_by,
            limit=limit,
            near_text=self._parse_near_text(
                near_text,
                certainty,
                distance,
                move_away=move_away,
                move_to=move_to,
                target_vector=target_vector,
            ),
            object_limit=object_limit,
            objects_count=objects_count,
        )
        return self.__call(request)

    def near_vector(
        self,
        *,
        near_vector: NearVectorInputType,
        certainty: Optional[NUMBER],
        distance: Optional[NUMBER],
        target_vector: Optional[TargetVectorJoinType],
        aggregations: List[aggregate_pb2.AggregateRequest.Aggregation],
        filters: Optional[base_pb2.Filters],
        group_by: Optional[aggregate_pb2.AggregateRequest.GroupBy],
        limit: Optional[int],
        object_limit: Optional[int],
        objects_count: bool,
    ) -> Awaitable[aggregate_pb2.AggregateReply]:
        if self._validate_arguments:
            self.__check_vector_search_args(
                certainty=certainty,
                distance=distance,
                object_limit=object_limit,
            )
        req = self.__create_request(
            aggregations=aggregations,
            filters=filters,
            group_by=group_by,
            limit=limit,
            near_vector=self._parse_near_vector(
                near_vector=near_vector,
                certainty=certainty,
                distance=distance,
                target_vector=target_vector,
            ),
            object_limit=object_limit,
            objects_count=objects_count,
        )
        return self.__call(req)

    def over_all(
        self,
        *,
        aggregations: List[aggregate_pb2.AggregateRequest.Aggregation],
        filters: Optional[base_pb2.Filters],
        group_by: Optional[aggregate_pb2.AggregateRequest.GroupBy],
        limit: Optional[int],
        objects_count: bool = False,
    ) -> Awaitable[aggregate_pb2.AggregateReply]:
        req = self.__create_request(
            aggregations=aggregations,
            filters=filters,
            group_by=group_by,
            limit=limit,
            objects_count=objects_count,
        )
        return self.__call(req)

    def __check_vector_search_args(
        self,
        *,
        certainty: Optional[NUMBER],
        distance: Optional[NUMBER],
        object_limit: Optional[int],
    ) -> None:
        if all([certainty is None, distance is None, object_limit is None]):
            raise WeaviateInvalidInputError(
                "You must provide at least one of the following arguments: certainty, distance, object_limit when vector searching"
            )

    def __create_request(
        self,
        *,
        aggregations: Optional[List[aggregate_pb2.AggregateRequest.Aggregation]] = None,
        filters: Optional[base_pb2.Filters] = None,
        group_by: Optional[aggregate_pb2.AggregateRequest.GroupBy] = None,
        hybrid: Optional[base_search_pb2.Hybrid] = None,
        limit: Optional[int] = None,
        near_object: Optional[base_search_pb2.NearObject] = None,
        near_text: Optional[base_search_pb2.NearTextSearch] = None,
        near_vector: Optional[base_search_pb2.NearVector] = None,
        object_limit: Optional[int] = None,
        objects_count: bool = False,
    ) -> aggregate_pb2.AggregateRequest:
        return aggregate_pb2.AggregateRequest(
            collection=self._name,
            aggregations=aggregations,
            filters=filters,
            group_by=group_by,
            hybrid=hybrid,
            limit=limit,
            near_object=near_object,
            near_text=near_text,
            near_vector=near_vector,
            object_limit=object_limit,
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
