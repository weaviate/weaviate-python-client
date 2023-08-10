import datetime
from dataclasses import dataclass
from typing import Optional, List, Dict, Union, Set

import grpc
import uuid as uuid_lib
from google.protobuf import struct_pb2
from typing_extensions import TypeAlias

from weaviate.collection.classes import _MetadataReturn, FilterValue, FilterOr, FilterAnd, Filters
from weaviate.connect import Connection
from weaviate.exceptions import WeaviateGRPCException
from weaviate.util import BaseEnum
from weaviate.weaviate_types import UUID
from weaviate_grpc import weaviate_pb2


class HybridFusion(str, BaseEnum):
    RANKED = "rankedFusion"
    RELATIVE_SCORE = "relativeScoreFusion"


@dataclass
class HybridOptions:
    alpha: Optional[float] = None
    vector: Optional[List[float]] = None
    properties: Optional[List[str]] = None
    fusion_type: Optional[HybridFusion] = None
    limit: Optional[int] = None
    autocut: Optional[int] = None


@dataclass
class GetOptions:
    limit: Optional[int] = None
    offset: Optional[int] = None
    after: Optional[UUID] = None


@dataclass
class BM25Options:
    properties: Optional[List[str]] = None
    limit: Optional[int] = None
    autocut: Optional[int] = None


@dataclass
class NearVectorOptions:
    certainty: Optional[float] = None
    distance: Optional[float] = None
    autocut: Optional[int] = None


@dataclass
class NearObjectOptions:
    certainty: Optional[float] = None
    distance: Optional[float] = None
    autocut: Optional[int] = None


@dataclass
class MetadataQuery:
    uuid: bool = False
    vector: bool = False
    creation_time_unix: bool = False
    last_update_time_unix: bool = False
    distance: bool = False
    certainty: bool = False
    score: bool = False
    explain_score: bool = False


@dataclass
class LinkTo:
    link_on: str
    properties: "PROPERTIES"
    metadata: MetadataQuery

    def __hash__(self):  # for set
        return hash(str(self))


PROPERTIES = Union[List[Union[str, LinkTo]], str]

# Can be found in the google.protobuf.internal.well_known_types.pyi stub file but is defined explicitly here for clarity.
_StructValue: TypeAlias = Union[struct_pb2.Struct, struct_pb2.ListValue, str, float, bool, None]


@dataclass
class GrpcResult:
    metadata: _MetadataReturn
    result: Dict[str, Union[_StructValue, List["GrpcResult"]]]


@dataclass
class ReturnValues:
    metadata: Optional[MetadataQuery] = None
    properties: Optional[PROPERTIES] = None


@dataclass
class RefProps:
    meta: MetadataQuery
    refs: Dict[str, "RefProps"]


@dataclass
class SearchResult:
    properties: weaviate_pb2.ResultProperties
    additional_properties: weaviate_pb2.ResultAdditionalProps


@dataclass
class SearchResponse:
    results: List[SearchResult]


class _GRPC:
    def __init__(
        self,
        connection: Connection,
        name: str,
        tenant: Optional[str] = None,
        default_properties: Optional[Set[str]] = None,
    ):
        self._connection: Connection = connection
        self._name: str = name
        self._tenant = tenant

        if default_properties is not None:
            self._default_props: Set[str] = default_properties
        else:
            self._default_props = set()
        self._metadata: Optional[MetadataQuery] = None

        self._limit: Optional[int] = None
        self._offset: Optional[int] = None
        self._autocut: Optional[int] = None
        self._after: Optional[UUID] = None

        self._hybrid_query: Optional[str] = None
        self._hybrid_alpha: Optional[float] = None
        self._hybrid_vector: Optional[List[float]] = None
        self._hybrid_properties: Optional[List[str]] = None
        self._hybrid_fusion_type: Optional[weaviate_pb2.HybridSearchParams.FusionType] = None

        self._bm25_query: Optional[str] = None
        self._bm25_properties: Optional[List[str]] = None

        self._near_vector_vec: Optional[List[float]] = None
        self._near_object_obj: Optional[UUID] = None
        self._near_certainty: Optional[float] = None
        self._near_distance: Optional[float] = None

        self._filters: Optional[Filters] = None

    def get(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ):
        self._limit = limit
        self._offset = offset
        self._after = after
        self._filters = filters
        self._metadata = return_metadata
        if return_properties is not None:
            self._default_props = self._default_props.union(return_properties)
        return self.__call()

    def hybrid(
        self,
        query: str,
        alpha: Optional[float] = None,
        vector: Optional[List[float]] = None,
        properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        limit: Optional[int] = None,
        autocut: Optional[int] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ):
        self._hybrid_query = query
        self._hybrid_alpha = alpha
        self._hybrid_vector = vector
        self._hybrid_properties = properties
        self._hybrid_fusion_type = (
            weaviate_pb2.HybridSearchParams.FusionType.Value(fusion_type.name)
            if fusion_type is not None
            else None
        )
        self._limit = limit
        self._autocut = autocut
        self._metadata = return_metadata
        if return_properties is not None:
            self._default_props = self._default_props.union(return_properties)

        return self.__call()

    def bm25(
        self,
        query: str,
        properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        autocut: Optional[int] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ):
        self._bm25_query = query
        self._bm25_properties = properties
        self._limit = limit
        self._autocut = autocut
        self._metadata = return_metadata
        if return_properties is not None:
            self._default_props = self._default_props.union(return_properties)

        return self.__call()

    def near_vector(
        self,
        vector: List[float],
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        autocut: Optional[int] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ):
        self._near_vector_vec = vector
        self._near_certainty = certainty
        self._near_distance = distance
        self._autocut = autocut
        self._metadata = return_metadata
        if return_properties is not None:
            self._default_props = self._default_props.union(return_properties)

        return self.__call()

    def near_object(
        self,
        near_object: UUID,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        autocut: Optional[int] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ):
        self._near_object_obj = near_object
        self._near_certainty = certainty
        self._near_distance = distance
        self._autocut = autocut

        self._metadata = return_metadata
        if return_properties is not None:
            self._default_props = self._default_props.union(return_properties)

        return self.__call()

    def __call(self):
        metadata = ()
        access_token = self._connection.get_current_bearer_token()
        if len(access_token) > 0:
            metadata = (("authorization", access_token),)
        try:
            res: SearchResponse  # According to PEP-0526
            res, _ = self._connection.grpc_stub.Search.with_call(
                weaviate_pb2.SearchRequest(
                    class_name=self._name,
                    limit=self._limit,
                    offset=self._offset,
                    after=str(self._after) if self._after is not None else "",
                    autocut=self._autocut,
                    near_vector=weaviate_pb2.NearVectorParams(
                        vector=self._near_vector_vec,
                        certainty=self._near_certainty,
                        distance=self._near_distance,
                    )
                    if self._near_vector_vec is not None
                    else None,
                    near_object=weaviate_pb2.NearObjectParams(
                        id=str(self._near_object_obj),
                        certainty=self._near_certainty,
                        distance=self._near_distance,
                    )
                    if self._near_object_obj is not None
                    else None,
                    properties=self._convert_references_to_grpc(self._default_props),
                    additional_properties=self._metadata_to_grpc(self._metadata)
                    if self._metadata is not None
                    else None,
                    bm25_search=weaviate_pb2.BM25SearchParams(
                        properties=self._bm25_properties, query=self._bm25_query
                    )
                    if self._bm25_query is not None
                    else None,
                    hybrid_search=weaviate_pb2.HybridSearchParams(
                        properties=self._hybrid_properties,
                        query=self._hybrid_query,
                        alpha=self._hybrid_alpha,
                        vector=self._hybrid_vector,
                        fusion_type=self._hybrid_fusion_type,
                    )
                    if self._hybrid_query is not None
                    else None,
                    tenant=self._tenant,
                    filters=self.__extract_filters(self._filters),
                ),
                metadata=metadata,
            )

            objects: List[GrpcResult] = []
            for result in res.results:
                obj = self._convert_references_to_grpc_result(result.properties)
                metadata_return = self.__extract_metadata_for_object(result.additional_properties)
                objects.append(GrpcResult(result=obj, metadata=metadata_return))

            return objects

        except grpc.RpcError as e:
            raise WeaviateGRPCException(e.details())

    def __extract_filters(self, weav_filter: Filters) -> Optional[weaviate_pb2.Filters]:
        if weav_filter is None:
            return None
        from google.protobuf.timestamp_pb2 import Timestamp

        if isinstance(weav_filter, FilterValue):
            timestamp = Timestamp()

            if isinstance(weav_filter.value, datetime.date):
                timestamp.FromDatetime(weav_filter.value)
            return weaviate_pb2.Filters(
                operator=weav_filter.operator.value,
                value_str=weav_filter.value if isinstance(weav_filter.value, str) else None,
                value_int=weav_filter.value if isinstance(weav_filter.value, int) else None,
                value_bool=weav_filter.value if isinstance(weav_filter.value, bool) else None,
                value_date=timestamp if isinstance(weav_filter.value, datetime.date) else None,
                value_float=weav_filter.value if isinstance(weav_filter.value, float) else None,
                on=weav_filter.path if isinstance(weav_filter.path, list) else [weav_filter.path],
            )

        else:
            assert isinstance(weav_filter, FilterAnd) or isinstance(weav_filter, FilterOr)
            return weaviate_pb2.Filters(
                operator=weav_filter.operator,
                filters=[
                    self.__extract_filters(single_filter) for single_filter in weav_filter.filters
                ],
            )

    def _ref_props_return_meta(self, props: PROPERTIES) -> Dict[str, RefProps]:
        ref_props = {}
        for prop in props:
            if isinstance(prop, LinkTo):
                ref_props[prop.link_on] = RefProps(
                    meta=prop.metadata, refs=self._ref_props_return_meta(prop.properties)
                )
        return ref_props

    def _metadata_to_grpc(self, metadata: MetadataQuery) -> weaviate_pb2.AdditionalProperties:
        return weaviate_pb2.AdditionalProperties(
            uuid=metadata.uuid,
            vector=metadata.vector,
            creationTimeUnix=metadata.creation_time_unix,
            lastUpdateTimeUnix=metadata.last_update_time_unix,
            distance=metadata.distance,
            certainty=metadata.certainty,
            explainScore=metadata.explain_score,
            score=metadata.score,
        )

    def _convert_references_to_grpc_result(self, properties: "weaviate_pb2.ResultProperties"):
        result: Dict[str, Union[_StructValue, List["GrpcResult"]]] = {}
        for name, non_ref_prop in properties.non_ref_properties.items():
            result[name] = non_ref_prop

        for ref_prop in properties.ref_props:
            result[ref_prop.prop_name] = [
                GrpcResult(
                    result=self._convert_references_to_grpc_result(prop),
                    metadata=self.__extract_metadata_for_object(prop.metadata),
                )
                for prop in ref_prop.properties
            ]

        return result

    def _convert_references_to_grpc(
        self, properties: Set[Union[LinkTo, str]]
    ) -> "weaviate_pb2.Properties":
        return weaviate_pb2.Properties(
            non_ref_properties=[prop for prop in properties if isinstance(prop, str)],
            ref_properties=[
                weaviate_pb2.RefProperties(
                    reference_property=prop.link_on,
                    linked_properties=self._convert_references_to_grpc(set(prop.properties)),
                    metadata=self._metadata_to_grpc(prop.metadata),
                )
                for prop in properties
                if isinstance(prop, LinkTo)
            ],
        )

    @staticmethod
    def __extract_metadata_for_object(
        add_props: "weaviate_pb2.ResultAdditionalProps",
    ) -> _MetadataReturn:
        return _MetadataReturn(
            uuid=uuid_lib.UUID(add_props.id) if len(add_props.id) > 0 else None,
            vector=[float(num) for num in add_props.vector] if len(add_props.vector) > 0 else None,
            distance=add_props.distance if add_props.distance_present else None,
            certainty=add_props.certainty if add_props.certainty_present else None,
            creation_time_unix=add_props.creation_time_unix
            if add_props.creation_time_unix_present
            else None,
            last_update_time_unix=add_props.last_update_time_unix
            if add_props.last_update_time_unix_present
            else None,
            score=add_props.score if add_props.score_present else None,
            explain_score=add_props.explain_score if add_props.explain_score_present else None,
        )
