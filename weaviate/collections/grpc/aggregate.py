from typing import List, Literal, Optional, Union

from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.grpc import (
    TargetVectorJoinType,
    NearVectorInputType,
    Move,
    HybridVectorType,
)
from weaviate.collections.grpc.shared import _BaseGRPC
from weaviate.connect import executor
from weaviate.connect.v4 import Connection
from weaviate.exceptions import (
    WeaviateInvalidInputError,
)
from weaviate.proto.v1 import aggregate_pb2, base_pb2, base_search_pb2
from weaviate.types import NUMBER, UUID
from weaviate.util import _ServerVersion


class _AggregateGRPC(_BaseGRPC):
    def __init__(
        self,
        weaviate_version: _ServerVersion,
        name: str,
        tenant: Optional[str],
        consistency_level: Optional[ConsistencyLevel],
        validate_arguments: bool,
    ):
        super().__init__(weaviate_version, consistency_level, validate_arguments)
        self._name: str = name
        self._tenant = tenant

    def objects_count(self, connection: Connection) -> executor.Result[int]:
        def resp(res: aggregate_pb2.AggregateReply) -> int:
            return res.single_result.objects_count

        return executor.execute(
            response_callback=resp,
            method=connection.grpc_aggregate,
            request=self.__create_request(objects_count=True),
        )

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
    ) -> aggregate_pb2.AggregateRequest:
        return self.__create_request(
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
    ) -> aggregate_pb2.AggregateRequest:
        if self._validate_arguments:
            self.__check_vector_search_args(
                certainty=certainty,
                distance=distance,
                object_limit=object_limit,
            )
        return self.__create_request(
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
    ) -> aggregate_pb2.AggregateRequest:
        if self._validate_arguments:
            self.__check_vector_search_args(
                certainty=certainty,
                distance=distance,
                object_limit=object_limit,
            )
        return self.__create_request(
            aggregations=aggregations,
            filters=filters,
            group_by=group_by,
            limit=limit,
            near_object=self._parse_near_object(near_object, certainty, distance, target_vector),
            object_limit=object_limit,
            objects_count=objects_count,
        )

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
    ) -> aggregate_pb2.AggregateRequest:
        if self._validate_arguments:
            self.__check_vector_search_args(
                certainty=certainty,
                distance=distance,
                object_limit=object_limit,
            )
        return self.__create_request(
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
    ) -> aggregate_pb2.AggregateRequest:
        if self._validate_arguments:
            self.__check_vector_search_args(
                certainty=certainty,
                distance=distance,
                object_limit=object_limit,
            )
        return self.__create_request(
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

    def over_all(
        self,
        *,
        aggregations: List[aggregate_pb2.AggregateRequest.Aggregation],
        filters: Optional[base_pb2.Filters],
        group_by: Optional[aggregate_pb2.AggregateRequest.GroupBy],
        limit: Optional[int],
        objects_count: bool = False,
    ) -> aggregate_pb2.AggregateRequest:
        return self.__create_request(
            aggregations=aggregations,
            filters=filters,
            group_by=group_by,
            limit=limit,
            objects_count=objects_count,
        )

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
