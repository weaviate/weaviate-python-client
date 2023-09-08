import datetime
import sys
from dataclasses import dataclass
from typing import (
    Any,
    Dict,
    Set,
    List,
    Optional,
    Union,
    Tuple,
    Type,
    Generic,
    cast,
)

from typing_extensions import TypeAlias

from weaviate.collection.classes.config import ConsistencyLevel
from weaviate.collection.extract_filters import FilterToGRPC

if sys.version_info < (3, 9):
    from typing_extensions import Annotated, get_type_hints, get_origin
else:
    from typing import Annotated, get_type_hints, get_origin

import grpc
import uuid as uuid_lib
from google.protobuf import struct_pb2

from weaviate.collection.classes.filters import (
    _Filters,
)
from weaviate.collection.classes.grpc import (
    GetOptions,
    HybridOptions,
    BM25Options,
    NearVectorOptions,
    NearObjectOptions,
    MetadataQuery,
    HybridFusion,
    PROPERTIES,
    LinkTo,
    LinkToMultiTarget,
    ReturnValues,
    NearImageOptions,
    NearAudioOptions,
    NearVideoOptions,
    Move,
    NearTextOptions,
)
from weaviate.collection.classes.internal import (
    _MetadataReturn,
    _Object,
    Reference,
    _extract_property_type_from_annotated_reference,
    _extract_property_type_from_reference,
    _extract_properties_from_data_model,
    _get_consistency_level,
    _GenerativeReturn,
)
from weaviate.collection.classes.orm import Model
from weaviate.collection.classes.types import (
    Properties,
)
from weaviate.connect import Connection
from weaviate.exceptions import WeaviateGRPCException
from weaviate.weaviate_types import UUID
from weaviate_grpc import weaviate_pb2

# Can be found in the google.protobuf.internal.well_known_types.pyi stub file but is defined explicitly here for clarity.
_StructValue: TypeAlias = Union[
    struct_pb2.Struct,
    struct_pb2.ListValue,
    str,
    float,
    bool,
    None,
    List[float],
    List[int],
    List[str],
    List[bool],
    List[UUID],
]
_PyValue: TypeAlias = Union[
    Dict[str, "_PyValue"],
    List["_PyValue"],
    str,
    float,
    bool,
    None,
    List[float],
    List[int],
    List[str],
    List[bool],
    List[UUID],
]


@dataclass
class GrpcResult:
    metadata: _MetadataReturn
    result: Dict[str, Union[_StructValue, List["GrpcResult"]]]


@dataclass
class SearchResult:
    properties: weaviate_pb2.ResultProperties
    additional_properties: weaviate_pb2.ResultAdditionalProps


@dataclass
class SearchResponse:
    # the name of these members must match the proto file
    results: List[SearchResult]
    generative_grouped_result: str


@dataclass
class _Move:
    force: float
    concepts: List[str]
    objects: List[uuid_lib.UUID]


class _GRPC:
    def __init__(
        self,
        connection: Connection,
        name: str,
        tenant: Optional[str],
        consistency_level: Optional[ConsistencyLevel],
        default_properties: Optional[PROPERTIES] = None,
    ):
        self._connection: Connection = connection
        self._name: str = name
        self._tenant = tenant
        self._consistency_level = consistency_level

        if default_properties is not None:
            self._default_props: Set[Union[str, LinkTo]] = set(default_properties)
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
        self._hybrid_fusion_type: Optional[int] = None

        self._bm25_query: Optional[str] = None
        self._bm25_properties: Optional[List[str]] = None

        self._near_vector_vec: Optional[List[float]] = None
        self._near_object_obj: Optional[UUID] = None
        self._near_text: Optional[List[str]] = None
        self._near_text_move_away: Optional[weaviate_pb2.NearTextSearchParams.Move] = None
        self._near_text_move_to: Optional[weaviate_pb2.NearTextSearchParams.Move] = None

        self._near_certainty: Optional[float] = None
        self._near_distance: Optional[float] = None

        self._near_image: Optional[str] = None
        self._near_video: Optional[str] = None
        self._near_audio: Optional[str] = None

        self._generative_single: Optional[str] = None
        self._generative_grouped: Optional[str] = None
        self._generative_grouped_properties: Optional[List[str]] = None

        self._filters: Optional[_Filters] = None

    def get(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[SearchResult]:
        self._limit = limit
        self._offset = offset
        self._after = after
        self._filters = filters
        self._metadata = return_metadata
        if return_properties is not None:
            self._default_props = self._default_props.union(return_properties)
        return cast(List[SearchResult], self.__call().results)

    def hybrid(
        self,
        query: str,
        alpha: Optional[float] = None,
        vector: Optional[List[float]] = None,
        properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        limit: Optional[int] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[SearchResult]:
        self._hybrid_query = query
        self._hybrid_alpha = alpha
        self._hybrid_vector = vector
        self._hybrid_properties = properties
        self._hybrid_fusion_type = (
            weaviate_pb2.HybridSearchParams.FusionType.Value(fusion_type.value)
            if fusion_type is not None
            else None
        )
        self._limit = limit
        self._autocut = autocut
        self._filters = filters
        self._metadata = return_metadata
        if return_properties is not None:
            self._default_props = self._default_props.union(return_properties)

        return cast(List[SearchResult], self.__call().results)

    def bm25(
        self,
        query: str,
        properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[SearchResult]:
        self._bm25_query = query
        self._bm25_properties = properties
        self._limit = limit
        self._autocut = autocut
        self._filters = filters
        self._metadata = return_metadata
        if return_properties is not None:
            self._default_props = self._default_props.union(return_properties)

        return cast(List[SearchResult], self.__call().results)

    def near_vector(
        self,
        near_vector: List[float],
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[SearchResult]:
        self._near_vector_vec = near_vector
        self._near_certainty = certainty
        self._near_distance = distance
        self._autocut = autocut
        self._filters = filters
        self._metadata = return_metadata
        if return_properties is not None:
            self._default_props = self._default_props.union(return_properties)

        return cast(List[SearchResult], self.__call().results)

    def near_object(
        self,
        near_object: UUID,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[SearchResult]:
        self._near_object_obj = near_object
        self._near_certainty = certainty
        self._near_distance = distance
        self._autocut = autocut
        self._filters = filters
        self._metadata = return_metadata
        if return_properties is not None:
            self._default_props = self._default_props.union(return_properties)

        return cast(List[SearchResult], self.__call().results)

    def near_text(
        self,
        near_text: Union[List[str], str],
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        move_to: Optional[Move] = None,
        move_away: Optional[Move] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[SearchResult]:
        if isinstance(near_text, str):
            near_text = [near_text]
        self._near_text = near_text
        self._near_certainty = certainty
        self._near_distance = distance
        self._autocut = autocut
        self._filters = filters
        if move_away is not None:
            self._near_text_move_away = weaviate_pb2.NearTextSearchParams.Move(
                force=move_away.force,
                concepts=move_away.concepts_list,
                uuids=move_away.objects_list,
            )
        if move_to is not None:
            self._near_text_move_to = weaviate_pb2.NearTextSearchParams.Move(
                force=move_to.force, concepts=move_to.concepts_list, uuids=move_to.objects_list
            )
        self._metadata = return_metadata
        if return_properties is not None:
            self._default_props = self._default_props.union(return_properties)

        return cast(List[SearchResult], self.__call().results)

    def near_image(
        self,
        image: str,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[SearchResult]:
        self._near_image = image
        self._near_certainty = certainty
        self._near_distance = distance
        self._autocut = autocut
        self._filters = filters

        self._metadata = return_metadata
        if return_properties is not None:
            self._default_props = self._default_props.union(return_properties)

        return cast(List[SearchResult], self.__call().results)

    def near_video(
        self,
        video: str,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[SearchResult]:
        self._near_video = video
        self._near_certainty = certainty
        self._near_distance = distance
        self._autocut = autocut
        self._filters = filters

        self._metadata = return_metadata
        if return_properties is not None:
            self._default_props = self._default_props.union(return_properties)

        return cast(List[SearchResult], self.__call().results)

    def near_audio(
        self,
        audio: str,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[SearchResult]:
        self._near_audio = audio
        self._near_certainty = certainty
        self._near_distance = distance
        self._autocut = autocut
        self._filters = filters

        self._metadata = return_metadata
        if return_properties is not None:
            self._default_props = self._default_props.union(return_properties)
        return cast(List[SearchResult], self.__call().results)

    def generative(
        self,
        single: Optional[str] = None,
        grouped: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> SearchResponse:
        if single is None and grouped is None:
            raise ValueError(
                "Either single_response or grouped response must be not None for generative search."
            )

        self._generative_single = single
        self._generative_grouped = grouped
        self._generative_grouped_properties = grouped_properties
        self._autocut = auto_limit
        self._filters = filters

        self._metadata = return_metadata
        if return_properties is not None:
            self._default_props = self._default_props.union(return_properties)

        return self.__call()

    def __call(self) -> SearchResponse:
        metadata: Optional[Tuple[Tuple[str, str]]] = None
        access_token = self._connection.get_current_bearer_token()
        if len(access_token) > 0:
            metadata = (("authorization", access_token),)
        try:
            assert self._connection.grpc_stub is not None
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
                        fusion_type=cast(
                            weaviate_pb2.HybridSearchParams.FusionType, self._hybrid_fusion_type
                        ),
                    )
                    if self._hybrid_query is not None
                    else None,
                    tenant=self._tenant,
                    filters=FilterToGRPC.convert(self._filters),
                    near_text=weaviate_pb2.NearTextSearchParams(
                        query=self._near_text,
                        certainty=self._near_certainty,
                        distance=self._near_distance,
                        move_to=self._near_text_move_to,
                        move_away=self._near_text_move_away,
                    )
                    if self._near_text is not None
                    else None,
                    near_image=weaviate_pb2.NearImageSearchParams(
                        image=self._near_image,
                        distance=self._near_distance,
                        certainty=self._near_certainty,
                    )
                    if self._near_image is not None
                    else None,
                    near_video=weaviate_pb2.NearVideoSearchParams(
                        video=self._near_video,
                        distance=self._near_distance,
                        certainty=self._near_certainty,
                    )
                    if self._near_video is not None
                    else None,
                    near_audio=weaviate_pb2.NearAudioSearchParams(
                        audio=self._near_audio,
                        distance=self._near_distance,
                        certainty=self._near_certainty,
                    )
                    if self._near_audio is not None
                    else None,
                    consistency_level=_get_consistency_level(self._consistency_level),
                    generative=weaviate_pb2.GenerativeSearch(
                        single_response_prompt=self._generative_single,
                        grouped_response_task=self._generative_grouped,
                        grouped_properties=self._generative_grouped_properties,
                    )
                    if self._generative_single is not None or self._generative_grouped is not None
                    else None,
                ),
                metadata=metadata,
            )

            return res

        except grpc.RpcError as e:
            raise WeaviateGRPCException(e.details())

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
            is_consistent=metadata.is_consistent,
        )

    def _convert_references_to_grpc(
        self, properties: Set[Union[LinkTo, LinkToMultiTarget, str]]
    ) -> "weaviate_pb2.Properties":
        return weaviate_pb2.Properties(
            non_ref_properties=[prop for prop in properties if isinstance(prop, str)],
            ref_properties=[
                weaviate_pb2.RefProperties(
                    reference_property=prop.link_on,
                    linked_properties=self._convert_references_to_grpc(set(prop.properties)),
                    metadata=self._metadata_to_grpc(prop.metadata),
                    which_collection=prop.target_collection
                    if isinstance(prop, LinkToMultiTarget)
                    else None,
                )
                for prop in properties
                if isinstance(prop, LinkTo)
            ],
        )


class _Grpc:
    def __init__(
        self,
        connection: Connection,
        name: str,
        consistency_level: Optional[ConsistencyLevel],
        tenant: Optional[str],
    ):
        self.__connection = connection
        self.__name = name
        self.__tenant = tenant
        self.__consistency_level = consistency_level

    def _query(self) -> _GRPC:
        return _GRPC(self.__connection, self.__name, self.__tenant, self.__consistency_level)

    @staticmethod
    def _extract_metadata_for_object(
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
            is_consistent=add_props.is_consistent,
            generative=add_props.generative if add_props.generative_present else None,
        )

    def _deserialize_primitive(self, value: Any, type_value: Any) -> Any:
        if type_value == uuid_lib.UUID:
            return uuid_lib.UUID(value)
        if type_value == datetime.datetime:
            return datetime.datetime.fromisoformat(value)
        if isinstance(type_value, list):
            return [
                self._deserialize_primitive(val, type_value[idx]) for idx, val in enumerate(value)
            ]
        return value


class _GrpcCollection(_Grpc):
    def __parse_result(
        self, properties: "weaviate_pb2.ResultProperties", type_: Optional[Type[Properties]]
    ) -> Properties:
        hints = get_type_hints(type_) if get_origin(type_) is not dict and type_ is not None else {}
        result = {}

        for name, non_ref_prop in properties.non_ref_properties.items():
            result[name] = self._deserialize_primitive(non_ref_prop, hints.get(name))

        for number_array_property in properties.number_array_properties:
            result[number_array_property.prop_name] = [
                float(val) for val in number_array_property.values
            ]

        for int_array_property in properties.int_array_properties:
            result[int_array_property.prop_name] = [int(val) for val in int_array_property.values]

        for text_array_property in properties.text_array_properties:
            result[text_array_property.prop_name] = [str(val) for val in text_array_property.values]

        for boolean_array_property in properties.boolean_array_properties:
            result[boolean_array_property.prop_name] = [
                bool(val) for val in boolean_array_property.values
            ]

        for ref_prop in properties.ref_props:
            hint = hints.get(ref_prop.prop_name)
            if hint is not None:
                if get_origin(hint) is Annotated:
                    referenced_property_type = _extract_property_type_from_annotated_reference(hint)
                else:
                    assert get_origin(hint) is Reference
                    referenced_property_type = _extract_property_type_from_reference(hint)
                result[ref_prop.prop_name] = Reference._from(
                    [
                        _Object(
                            properties=self.__parse_result(prop, referenced_property_type),
                            metadata=self._extract_metadata_for_object(prop.metadata),
                        )
                        for prop in ref_prop.properties
                    ]
                )
            else:
                result[ref_prop.prop_name] = Reference[Dict[str, Any]]._from(
                    [
                        _Object(
                            properties=self.__parse_result(prop, Dict[str, Any]),
                            metadata=self._extract_metadata_for_object(prop.metadata),
                        )
                        for prop in ref_prop.properties
                    ]
                )

        return cast(Properties, result)

    def __result_to_object(
        self, res: SearchResult, type_: Optional[Type[Properties]]
    ) -> _Object[Properties]:
        properties = self.__parse_result(res.properties, type_)
        metadata = self._extract_metadata_for_object(res.additional_properties)
        return _Object[Properties](properties=properties, metadata=metadata)

    def __determine_generic(
        self, type_: Union[PROPERTIES, Type[Properties], None]
    ) -> Tuple[Optional[PROPERTIES], Type[Properties]]:
        if isinstance(type_, list) or isinstance(type_, str) or type_ is None:
            ret_properties = cast(Optional[PROPERTIES], type_)
            ret_type = cast(Type[Properties], Dict[str, Any])
        else:
            assert get_origin(type_) is not dict
            type_ = cast(Type[Properties], type_)
            ret_properties = _extract_properties_from_data_model(type_)
            ret_type = type_
        return ret_properties, ret_type

    def get_flat(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> List[_Object[Properties]]:
        ret_properties, ret_type = self.__determine_generic(return_properties)
        return [
            self.__result_to_object(obj, ret_type)
            for obj in self._query().get(
                limit=limit,
                offset=offset,
                after=after,
                filters=filters,
                return_metadata=return_metadata,
                return_properties=ret_properties,
            )
        ]

    def get_options(
        self,
        returns: ReturnValues,
        options: Optional[GetOptions],
    ) -> List[_Object[Properties]]:
        if options is None:
            options = GetOptions()
        ret_properties, ret_type = self.__determine_generic(returns.properties)
        return [
            self.__result_to_object(obj, ret_type)
            for obj in self._query().get(
                limit=options.limit,
                offset=options.offset,
                after=options.after,
                filters=options.filters,
                return_metadata=returns.metadata,
                return_properties=ret_properties,
            )
        ]

    def hybrid_flat(
        self,
        query: str,
        alpha: Optional[float] = None,
        vector: Optional[List[float]] = None,
        query_properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> List[_Object[Properties]]:
        ret_properties, ret_type = self.__determine_generic(return_properties)
        return [
            self.__result_to_object(obj, ret_type)
            for obj in self._query().hybrid(
                query=query,
                alpha=alpha,
                vector=vector,
                properties=query_properties,
                fusion_type=fusion_type,
                limit=limit,
                autocut=auto_limit,
                filters=filters,
                return_metadata=return_metadata,
                return_properties=ret_properties,
            )
        ]

    def hybrid_options(
        self,
        query: str,
        returns: ReturnValues,
        options: Optional[HybridOptions] = None,
    ) -> List[_Object[Properties]]:
        if options is None:
            options = HybridOptions()
        ret_properties, ret_type = self.__determine_generic(returns.properties)
        return [
            self.__result_to_object(obj, ret_type)
            for obj in self._query().hybrid(
                query=query,
                alpha=options.alpha,
                vector=options.vector,
                properties=options.properties,
                fusion_type=options.fusion_type,
                limit=options.limit,
                autocut=options.auto_limit,
                filters=options.filters,
                return_metadata=returns.metadata,
                return_properties=ret_properties,
            )
        ]

    def bm25_flat(
        self,
        query: str,
        query_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> List[_Object[Properties]]:
        ret_properties, ret_type = self.__determine_generic(return_properties)
        return [
            self.__result_to_object(obj, ret_type)
            for obj in self._query().bm25(
                query=query,
                properties=query_properties,
                limit=limit,
                autocut=auto_limit,
                filters=filters,
                return_metadata=return_metadata,
                return_properties=ret_properties,
            )
        ]

    def bm25_options(
        self,
        query: str,
        returns: ReturnValues,
        options: Optional[BM25Options] = None,
    ) -> List[_Object[Properties]]:
        if options is None:
            options = BM25Options()
        ret_properties, ret_type = self.__determine_generic(returns.properties)
        return [
            self.__result_to_object(obj, ret_type)
            for obj in self._query().bm25(
                query=query,
                properties=options.properties,
                limit=options.limit,
                autocut=options.auto_limit,
                filters=options.filters,
                return_metadata=returns.metadata,
                return_properties=ret_properties,
            )
        ]

    def near_vector_flat(
        self,
        near_vector: List[float],
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> List[_Object[Properties]]:
        ret_properties, ret_type = self.__determine_generic(return_properties)
        return [
            self.__result_to_object(obj, ret_type)
            for obj in self._query().near_vector(
                near_vector=near_vector,
                certainty=certainty,
                distance=distance,
                autocut=auto_limit,
                filters=filters,
                return_metadata=return_metadata,
                return_properties=ret_properties,
            )
        ]

    def near_vector_options(
        self,
        near_vector: List[float],
        returns: ReturnValues,
        options: Optional[NearVectorOptions] = None,
    ) -> List[_Object[Properties]]:
        if options is None:
            options = NearVectorOptions()
        ret_properties, ret_type = self.__determine_generic(returns.properties)
        return [
            self.__result_to_object(obj, ret_type)
            for obj in self._query().near_vector(
                near_vector=near_vector,
                certainty=options.certainty,
                distance=options.distance,
                autocut=options.auto_limit,
                filters=options.filters,
                return_metadata=returns.metadata,
                return_properties=ret_properties,
            )
        ]

    def near_object_flat(
        self,
        near_object: UUID,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> List[_Object[Properties]]:
        ret_properties, ret_type = self.__determine_generic(return_properties)
        return [
            self.__result_to_object(obj, ret_type)
            for obj in self._query().near_object(
                near_object=near_object,
                certainty=certainty,
                distance=distance,
                autocut=auto_limit,
                filters=filters,
                return_metadata=return_metadata,
                return_properties=ret_properties,
            )
        ]

    def near_object_options(
        self,
        near_object: UUID,
        returns: ReturnValues,
        options: Optional[NearObjectOptions] = None,
    ) -> List[_Object[Properties]]:
        if options is None:
            options = NearObjectOptions()
        ret_properties, ret_type = self.__determine_generic(returns.properties)
        return [
            self.__result_to_object(obj, ret_type)
            for obj in self._query().near_object(
                near_object=near_object,
                certainty=options.certainty,
                distance=options.distance,
                autocut=options.auto_limit,
                filters=options.filters,
                return_metadata=returns.metadata,
                return_properties=ret_properties,
            )
        ]

    def near_text_flat(
        self,
        query: Union[List[str], str],
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        move_to: Optional[Move] = None,
        move_away: Optional[Move] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> List[_Object[Properties]]:
        ret_properties, ret_type = self.__determine_generic(return_properties)
        return [
            self.__result_to_object(obj, ret_type)
            for obj in self._query().near_text(
                near_text=query,
                certainty=certainty,
                distance=distance,
                move_to=move_to,
                move_away=move_away,
                autocut=auto_limit,
                filters=filters,
                return_metadata=return_metadata,
                return_properties=ret_properties,
            )
        ]

    def near_text_options(
        self,
        query: Union[List[str], str],
        returns: ReturnValues[Properties],
        options: Optional[NearTextOptions] = None,
    ) -> List[_Object[Properties]]:
        if options is None:
            options = NearTextOptions()
        ret_properties, ret_type = self.__determine_generic(returns.properties)
        return [
            self.__result_to_object(obj, ret_type)
            for obj in self._query().near_text(
                near_text=query,
                certainty=options.certainty if options is not None else None,
                distance=options.distance if options is not None else None,
                move_to=options.move_to if options is not None else None,
                move_away=options.move_away if options is not None else None,
                autocut=options.auto_limit if options is not None else None,
                filters=options.filters if options is not None else None,
                return_metadata=returns.metadata,
                return_properties=ret_properties,
            )
        ]

    def near_image_flat(
        self,
        image: str,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> List[_Object[Properties]]:
        ret_properties, ret_type = self.__determine_generic(return_properties)
        return [
            self.__result_to_object(obj, ret_type)
            for obj in self._query().near_image(
                image=image,
                certainty=certainty,
                distance=distance,
                filters=filters,
                autocut=auto_limit,
                return_metadata=return_metadata,
                return_properties=ret_properties,
            )
        ]

    def near_image_options(
        self,
        image: str,
        returns: ReturnValues[Properties],
        options: Optional[NearImageOptions] = None,
    ) -> List[_Object[Properties]]:
        if options is None:
            options = NearImageOptions()
        ret_properties, ret_type = self.__determine_generic(returns.properties)
        return [
            self.__result_to_object(obj, ret_type)
            for obj in self._query().near_image(
                image=image,
                certainty=options.certainty if options is not None else None,
                distance=options.distance if options is not None else None,
                filters=options.filters if options is not None else None,
                autocut=options.auto_limit if options is not None else None,
                return_metadata=returns.metadata,
                return_properties=ret_properties,
            )
        ]

    def near_audio_flat(
        self,
        audio: str,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> List[_Object[Properties]]:
        ret_properties, ret_type = self.__determine_generic(return_properties)
        return [
            self.__result_to_object(obj, ret_type)
            for obj in self._query().near_audio(
                audio=audio,
                certainty=certainty,
                distance=distance,
                filters=filters,
                autocut=auto_limit,
                return_metadata=return_metadata,
                return_properties=ret_properties,
            )
        ]

    def near_audio_options(
        self,
        audio: str,
        returns: ReturnValues[Properties],
        options: Optional[NearAudioOptions] = None,
    ) -> List[_Object[Properties]]:
        if options is None:
            options = NearAudioOptions()
        ret_properties, ret_type = self.__determine_generic(returns.properties)
        return [
            self.__result_to_object(obj, ret_type)
            for obj in self._query().near_image(
                image=audio,
                certainty=options.certainty if options is not None else None,
                distance=options.distance if options is not None else None,
                filters=options.filters if options is not None else None,
                autocut=options.auto_limit if options is not None else None,
                return_metadata=returns.metadata,
                return_properties=ret_properties,
            )
        ]

    def near_video_flat(
        self,
        video: str,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> List[_Object[Properties]]:
        ret_properties, ret_type = self.__determine_generic(return_properties)
        return [
            self.__result_to_object(obj, ret_type)
            for obj in self._query().near_video(
                video=video,
                certainty=certainty,
                distance=distance,
                filters=filters,
                autocut=auto_limit,
                return_metadata=return_metadata,
                return_properties=ret_properties,
            )
        ]

    def near_video_options(
        self,
        video: str,
        returns: ReturnValues[Properties],
        options: Optional[NearVideoOptions] = None,
    ) -> List[_Object[Properties]]:
        if options is None:
            options = NearVideoOptions()
        ret_properties, ret_type = self.__determine_generic(returns.properties)
        return [
            self.__result_to_object(obj, ret_type)
            for obj in self._query().near_video(
                video=video,
                certainty=options.certainty if options is not None else None,
                distance=options.distance if options is not None else None,
                filters=options.filters if options is not None else None,
                autocut=options.auto_limit if options is not None else None,
                return_metadata=returns.metadata,
                return_properties=ret_properties,
            )
        ]

    def generative(
        self,
        single: Optional[str] = None,
        grouped: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> _GenerativeReturn[Properties]:
        ret_properties, ret_type = self.__determine_generic(return_properties)
        ret = self._query().generative(
            single=single,
            grouped=grouped,
            grouped_properties=grouped_properties,
            filters=filters,
            auto_limit=auto_limit,
            return_metadata=return_metadata,
            return_properties=ret_properties,
        )
        objects = [self.__result_to_object(obj, ret_type) for obj in ret.results]
        grouped_results = (
            ret.generative_grouped_result if ret.generative_grouped_result != "" else None
        )
        return _GenerativeReturn[Properties](objects=objects, generative_group=grouped_results)


class _GrpcCollectionModel(Generic[Model], _Grpc):
    def __init__(
        self,
        connection: Connection,
        name: str,
        model: Type[Model],
        tenant: Optional[str] = None,
        consistency_level: Optional[ConsistencyLevel] = None,
    ):
        super().__init__(connection, name, consistency_level, tenant)
        self.model = model

    def __parse_result(
        self,
        properties: "weaviate_pb2.ResultProperties",
        type_: Type[Model],
    ) -> Model:
        hints = get_type_hints(type_)

        result = {}

        for name, non_ref_prop in properties.non_ref_properties.items():
            result[name] = self._deserialize_primitive(non_ref_prop, hints.get(name))

        for ref_prop in properties.ref_props:
            hint = hints.get(ref_prop.prop_name)
            if hint is not None:
                referenced_property_type = (lambda: "TODO: implement this")()
                result[ref_prop.prop_name] = [
                    _Object(
                        properties=self.__parse_result(
                            prop, cast(Type[Model], referenced_property_type)
                        ),
                        metadata=self._extract_metadata_for_object(prop.metadata),
                    )
                    for prop in ref_prop.properties
                ]
            else:
                raise ValueError(
                    f"Property {ref_prop.prop_name} is not defined with a Reference[Model] type hint in the model {self.model}"
                )

        return type_(**result)

    def __result_to_object(self, res: SearchResult) -> _Object[Model]:
        properties = self.__parse_result(res.properties, self.model)
        metadata = self._extract_metadata_for_object(res.additional_properties)
        return _Object[Model](properties=properties, metadata=metadata)

    def get_flat(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[_Object[Model]]:
        return [
            self.__result_to_object(obj)
            for obj in self._query().get(
                limit=limit,
                offset=offset,
                after=after,
                filters=filters,
                return_metadata=return_metadata,
                return_properties=return_properties,
            )
        ]

    def get_options(
        self,
        returns: ReturnValues[Model],
        options: Optional[GetOptions],
    ) -> List[_Object[Model]]:
        if options is None:
            options = GetOptions()
        return [
            self.__result_to_object(obj)
            for obj in self._query().get(
                limit=options.limit if options is not None else None,
                offset=options.offset if options is not None else None,
                after=options.after if options is not None else None,
                filters=options.filters if options is not None else None,
                return_metadata=returns.metadata,
                return_properties=cast(Optional[PROPERTIES], returns.properties),
            )
        ]

    def hybrid_flat(
        self,
        query: str,
        alpha: Optional[float] = None,
        vector: Optional[List[float]] = None,
        query_properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[_Object[Model]]:
        return [
            self.__result_to_object(obj)
            for obj in self._query().hybrid(
                query=query,
                alpha=alpha,
                vector=vector,
                properties=query_properties,
                fusion_type=fusion_type,
                limit=limit,
                autocut=auto_limit,
                filters=filters,
                return_metadata=return_metadata,
                return_properties=return_properties,
            )
        ]

    def hybrid_options(
        self,
        query: str,
        returns: ReturnValues[Model],
        options: Optional[HybridOptions] = None,
    ) -> List[_Object[Model]]:
        if options is None:
            options = HybridOptions()
        return [
            self.__result_to_object(obj)
            for obj in self._query().hybrid(
                query=query,
                alpha=options.alpha if options is not None else None,
                vector=options.vector if options is not None else None,
                properties=options.properties if options is not None else None,
                fusion_type=options.fusion_type if options is not None else None,
                limit=options.limit if options is not None else None,
                autocut=options.auto_limit if options is not None else None,
                filters=options.filters if options is not None else None,
                return_metadata=returns.metadata,
                return_properties=cast(Optional[PROPERTIES], returns.properties),
            )
        ]

    def bm25_flat(
        self,
        query: str,
        query_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[_Object[Model]]:
        return [
            self.__result_to_object(obj)
            for obj in self._query().bm25(
                query=query,
                properties=query_properties,
                limit=limit,
                autocut=auto_limit,
                filters=filters,
                return_metadata=return_metadata,
                return_properties=return_properties,
            )
        ]

    def bm25_options(
        self,
        query: str,
        returns: ReturnValues[Model],
        options: Optional[BM25Options] = None,
    ) -> List[_Object[Model]]:
        if options is None:
            options = BM25Options()
        return [
            self.__result_to_object(obj)
            for obj in self._query().bm25(
                query=query,
                properties=options.properties if options is not None else None,
                limit=options.limit if options is not None else None,
                autocut=options.auto_limit if options is not None else None,
                filters=options.filters if options is not None else None,
                return_metadata=returns.metadata,
                return_properties=cast(Optional[PROPERTIES], returns.properties),
            )
        ]

    def near_vector_flat(
        self,
        near_vector: List[float],
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[_Object[Model]]:
        return [
            self.__result_to_object(obj)
            for obj in self._query().near_vector(
                near_vector=near_vector,
                certainty=certainty,
                distance=distance,
                autocut=auto_limit,
                filters=filters,
                return_metadata=return_metadata,
                return_properties=return_properties,
            )
        ]

    def near_vector_options(
        self,
        near_vector: List[float],
        returns: ReturnValues[Model],
        options: Optional[NearVectorOptions] = None,
    ) -> List[_Object[Model]]:
        if options is None:
            options = NearVectorOptions()
        return [
            self.__result_to_object(obj)
            for obj in self._query().near_vector(
                near_vector=near_vector,
                certainty=options.certainty if options is not None else None,
                distance=options.distance if options is not None else None,
                autocut=options.auto_limit if options is not None else None,
                filters=options.filters if options is not None else None,
                return_metadata=returns.metadata,
                return_properties=cast(Optional[PROPERTIES], returns.properties),
            )
        ]

    def near_object_flat(
        self,
        near_object: UUID,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[_Object[Model]]:
        return [
            self.__result_to_object(obj)
            for obj in self._query().near_object(
                near_object=near_object,
                certainty=certainty,
                distance=distance,
                autocut=auto_limit,
                filters=filters,
                return_metadata=return_metadata,
                return_properties=return_properties,
            )
        ]

    def near_object_options(
        self,
        near_object: UUID,
        returns: ReturnValues[Model],
        options: Optional[NearObjectOptions] = None,
    ) -> List[_Object[Model]]:
        if options is None:
            options = NearObjectOptions()
        return [
            self.__result_to_object(obj)
            for obj in self._query().near_object(
                near_object=near_object,
                certainty=options.certainty if options is not None else None,
                distance=options.distance if options is not None else None,
                autocut=options.auto_limit if options is not None else None,
                filters=options.filters if options is not None else None,
                return_metadata=returns.metadata,
                return_properties=cast(Optional[PROPERTIES], returns.properties),
            )
        ]

    def near_text_flat(
        self,
        query: Union[List[str], str],
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        move_to: Optional[Move] = None,
        move_away: Optional[Move] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[_Object[Model]]:
        return [
            self.__result_to_object(obj)
            for obj in self._query().near_text(
                near_text=query,
                certainty=certainty,
                distance=distance,
                move_to=move_to,
                move_away=move_away,
                autocut=auto_limit,
                filters=filters,
                return_metadata=return_metadata,
                return_properties=return_properties,
            )
        ]

    def near_text_options(
        self,
        query: Union[List[str], str],
        returns: ReturnValues[Model],
        options: Optional[NearTextOptions] = None,
    ) -> List[_Object[Model]]:
        if options is None:
            options = NearTextOptions()

        return [
            self.__result_to_object(obj)
            for obj in self._query().near_text(
                near_text=query,
                certainty=options.certainty if options is not None else None,
                distance=options.distance if options is not None else None,
                move_to=options.move_to if options is not None else None,
                move_away=options.move_away if options is not None else None,
                autocut=options.auto_limit if options is not None else None,
                filters=options.filters if options is not None else None,
                return_metadata=returns.metadata,
                return_properties=cast(Optional[PROPERTIES], returns.properties),
            )
        ]

    def near_image_flat(
        self,
        image: str,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[_Object[Model]]:

        return [
            self.__result_to_object(obj)
            for obj in self._query().near_image(
                image=image,
                certainty=certainty,
                distance=distance,
                filters=filters,
                autocut=auto_limit,
                return_metadata=return_metadata,
                return_properties=return_properties,
            )
        ]

    def near_image_options(
        self,
        image: str,
        returns: ReturnValues[Model],
        options: Optional[NearImageOptions] = None,
    ) -> List[_Object[Model]]:
        if options is None:
            options = NearImageOptions()

        return [
            self.__result_to_object(obj)
            for obj in self._query().near_image(
                image=image,
                certainty=options.certainty if options is not None else None,
                distance=options.distance if options is not None else None,
                filters=options.filters if options is not None else None,
                autocut=options.auto_limit if options is not None else None,
                return_metadata=returns.metadata,
                return_properties=cast(Optional[PROPERTIES], returns.properties),
            )
        ]

    def near_audio_flat(
        self,
        audio: str,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[_Object[Model]]:

        return [
            self.__result_to_object(obj)
            for obj in self._query().near_audio(
                audio=audio,
                certainty=certainty,
                distance=distance,
                filters=filters,
                autocut=auto_limit,
                return_metadata=return_metadata,
                return_properties=return_properties,
            )
        ]

    def near_audio_options(
        self,
        audio: str,
        returns: ReturnValues[Model],
        options: Optional[NearAudioOptions] = None,
    ) -> List[_Object[Model]]:
        if options is None:
            options = NearAudioOptions()

        return [
            self.__result_to_object(obj)
            for obj in self._query().near_image(
                image=audio,
                certainty=options.certainty if options is not None else None,
                distance=options.distance if options is not None else None,
                filters=options.filters if options is not None else None,
                autocut=options.auto_limit if options is not None else None,
                return_metadata=returns.metadata,
                return_properties=cast(Optional[PROPERTIES], returns.properties),
            )
        ]

    def near_video_flat(
        self,
        video: str,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[_Object[Model]]:

        return [
            self.__result_to_object(obj)
            for obj in self._query().near_video(
                video=video,
                certainty=certainty,
                distance=distance,
                filters=filters,
                autocut=auto_limit,
                return_metadata=return_metadata,
                return_properties=return_properties,
            )
        ]

    def near_video_options(
        self,
        video: str,
        returns: ReturnValues[Model],
        options: Optional[NearVideoOptions] = None,
    ) -> List[_Object[Model]]:
        if options is None:
            options = NearVideoOptions()

        return [
            self.__result_to_object(obj)
            for obj in self._query().near_video(
                video=video,
                certainty=options.certainty if options is not None else None,
                distance=options.distance if options is not None else None,
                filters=options.filters if options is not None else None,
                autocut=options.auto_limit if options is not None else None,
                return_metadata=returns.metadata,
                return_properties=cast(Optional[PROPERTIES], returns.properties),
            )
        ]
