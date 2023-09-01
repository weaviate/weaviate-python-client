import datetime
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
    get_origin,
    get_type_hints,
)
from typing_extensions import TypeAlias

import grpc
import uuid as uuid_lib
from google.protobuf import struct_pb2

from weaviate.collection.classes.filters import (
    _FilterValue,
    _Filters,
    _FilterAnd,
    _FilterOr,
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
    Properties,
    _extract_props_from_list_of_objects,
)
from weaviate.collection.classes.orm import Model
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
    results: List[SearchResult]


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
        default_properties: Optional[PROPERTIES] = None,
    ):
        self._connection: Connection = connection
        self._name: str = name
        self._tenant = tenant

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
    ) -> List[SearchResult]:
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
    ) -> List[SearchResult]:
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
    ) -> List[SearchResult]:
        self._near_object_obj = near_object
        self._near_certainty = certainty
        self._near_distance = distance
        self._autocut = autocut

        self._metadata = return_metadata
        if return_properties is not None:
            self._default_props = self._default_props.union(return_properties)

        return self.__call()

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
    ) -> List[GrpcResult]:
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

        return self.__call()

    def near_image(
        self,
        image: str,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[GrpcResult]:
        self._near_image = image
        self._near_certainty = certainty
        self._near_distance = distance
        self._autocut = autocut
        self._filters = filters

        self._metadata = return_metadata
        if return_properties is not None:
            self._default_props = self._default_props.union(return_properties)

        return self.__call()

    def near_video(
        self,
        video: str,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[GrpcResult]:
        self._near_video = video
        self._near_certainty = certainty
        self._near_distance = distance
        self._autocut = autocut
        self._filters = filters

        self._metadata = return_metadata
        if return_properties is not None:
            self._default_props = self._default_props.union(return_properties)

        return self.__call()

    def near_audio(
        self,
        audio: str,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[GrpcResult]:
        self._near_audio = audio
        self._near_certainty = certainty
        self._near_distance = distance
        self._autocut = autocut
        self._filters = filters

        self._metadata = return_metadata
        if return_properties is not None:
            self._default_props = self._default_props.union(return_properties)

        return self.__call()

    def __call(self) -> List[GrpcResult]:
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
                    filters=self.__extract_filters(self._filters),
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
                ),
                metadata=metadata,
            )

            return res.results

        except grpc.RpcError as e:
            raise WeaviateGRPCException(e.details())

    def __extract_filters(self, weav_filter: _Filters) -> Optional[weaviate_pb2.Filters]:
        if weav_filter is None:
            return None
        from google.protobuf.timestamp_pb2 import Timestamp

        if isinstance(weav_filter, _FilterValue):
            timestamp = Timestamp()

            if isinstance(weav_filter.value, datetime.date):
                timestamp.FromDatetime(weav_filter.value)

            return weaviate_pb2.Filters(
                operator=weav_filter.operator,
                value_text=weav_filter.value if isinstance(weav_filter.value, str) else None,
                value_int=weav_filter.value if isinstance(weav_filter.value, int) else None,
                value_boolean=weav_filter.value if isinstance(weav_filter.value, bool) else None,
                value_date=timestamp if isinstance(weav_filter.value, datetime.date) else None,
                value_number=weav_filter.value if isinstance(weav_filter.value, float) else None,
                value_int_array=weaviate_pb2.IntArray(vals=weav_filter.value)
                if isinstance(weav_filter.value, list) and isinstance(weav_filter.value[0], int)
                else None,
                value_number_array=weaviate_pb2.NumberArray(vals=weav_filter.value)
                if isinstance(weav_filter.value, list) and isinstance(weav_filter.value[0], float)
                else None,
                value_text_array=weaviate_pb2.TextArray(vals=weav_filter.value)
                if isinstance(weav_filter.value, list) and isinstance(weav_filter.value[0], str)
                else None,
                value_boolean_array=weaviate_pb2.BooleanArray(vals=weav_filter.value)
                if isinstance(weav_filter.value, list) and isinstance(weav_filter.value[0], bool)
                else None,
                on=weav_filter.path if isinstance(weav_filter.path, list) else [weav_filter.path],
            )

        else:
            assert isinstance(weav_filter, _FilterAnd) or isinstance(weav_filter, _FilterOr)
            return weaviate_pb2.Filters(
                operator=weav_filter.operator,
                filters=[
                    self.__extract_filters(single_filter) for single_filter in weav_filter.filters
                ],
            )

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
    def __init__(self, connection: Connection, name: str, tenant: Optional[str]):
        self.__connection = connection
        self.__name = name
        self.__tenant = tenant

    def _query(self) -> _GRPC:
        return _GRPC(self.__connection, self.__name, self.__tenant)

    def _struct_value_to_py_value(self, value: _StructValue) -> _PyValue:
        if isinstance(value, struct_pb2.Struct):
            return {key: self._struct_value_to_py_value(value) for key, value in value.items()}
        elif isinstance(value, struct_pb2.ListValue):
            return [
                self._struct_value_to_py_value(cast(_StructValue, value)) for value in value.values
            ]
        elif isinstance(value, str) or isinstance(value, float) or isinstance(value, bool):
            return value
        else:
            assert value is None
            return None

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
    def __init__(self, connection: Connection, name: str, tenant: Optional[str]):
        super().__init__(connection, name, tenant)

    def __parse_result(
        self, properties: "weaviate_pb2.ResultProperties", type_: Optional[Type[Properties]]
    ) -> Properties:
        hints = get_type_hints(type_) if get_origin(type_) is not dict and type_ is not None else {}

        result = {}

        for name, non_ref_prop in properties.non_ref_properties.items():
            result[name] = self._deserialize_primitive(non_ref_prop, hints.get(name))

        for number_array_property in properties.number_array_properties:
            result[number_array_property.key] = [float(val) for val in number_array_property.vals]

        for int_array_property in properties.int_array_properties:
            result[int_array_property.key] = [int(val) for val in int_array_property.vals]

        for text_array_property in properties.text_array_properties:
            result[text_array_property.key] = [str(val) for val in text_array_property.vals]

        for boolean_array_property in properties.boolean_array_properties:
            result[boolean_array_property.key] = [bool(val) for val in boolean_array_property.vals]

        for uuid_array_property in properties.uuid_array_properties:
            result[uuid_array_property.key] = [
                uuid_lib.UUID(val) for val in uuid_array_property.vals
            ]

        for ref_prop in properties.ref_props:
            hint = hints.get(ref_prop.prop_name)
            if hint is not None:
                referenced_property_type = _extract_props_from_list_of_objects(hint)
                result[ref_prop.prop_name] = [
                    _Object(
                        properties=self.__parse_result(prop, referenced_property_type),
                        metadata=self._extract_metadata_for_object(prop.metadata),
                    )
                    for prop in ref_prop.properties
                ]
            else:
                result[ref_prop.prop_name] = [
                    _Object(
                        properties=self.__parse_result(prop, Dict[str, Any]),
                        metadata=self._extract_metadata_for_object(prop.metadata),
                    )
                    for prop in ref_prop.properties
                ]

        return cast(Properties, result)

    def __result_to_object(
        self, res: SearchResult, type_: Optional[Type[Properties]]
    ) -> _Object[Properties]:
        properties = self.__parse_result(res.properties, type_)
        metadata = self._extract_metadata_for_object(res.additional_properties)
        return _Object[Properties](properties=properties, metadata=metadata)

    def get_flat(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
        data_model: Optional[Type[Properties]] = None,
    ) -> List[_Object[Properties]]:
        return [
            self.__result_to_object(obj, data_model)
            for obj in self._query().get(
                limit, offset, after, filters, return_metadata, return_properties
            )
        ]

    def get_options(
        self,
        returns: ReturnValues,
        options: Optional[GetOptions],
        filters: Optional[_Filters] = None,
        data_model: Optional[Type[Properties]] = None,
    ) -> List[_Object[Properties]]:
        if options is None:
            options = GetOptions()
        return [
            self.__result_to_object(obj, data_model)
            for obj in self._query().get(
                options.limit,
                options.offset,
                options.after,
                filters,
                returns.metadata,
                returns.properties,
            )
        ]

    def hybrid_flat(
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
        data_model: Optional[Type[Properties]] = None,
    ) -> List[_Object[Properties]]:
        return [
            self.__result_to_object(obj, data_model)
            for obj in self._query().hybrid(
                query,
                alpha,
                vector,
                properties,
                fusion_type,
                limit,
                autocut,
                return_metadata,
                return_properties,
            )
        ]

    def hybrid_options(
        self,
        query: str,
        returns: ReturnValues,
        options: Optional[HybridOptions] = None,
        data_model: Optional[Type[Properties]] = None,
    ) -> List[_Object[Properties]]:
        if options is None:
            options = HybridOptions()
        return [
            self.__result_to_object(obj, data_model)
            for obj in self._query().hybrid(
                query,
                options.alpha,
                options.vector,
                options.properties,
                options.fusion_type,
                options.limit,
                options.autocut,
                returns.metadata,
                returns.properties,
            )
        ]

    def bm25_flat(
        self,
        query: str,
        properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        autocut: Optional[int] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
        data_model: Optional[Type[Properties]] = None,
    ) -> List[_Object[Properties]]:
        return [
            self.__result_to_object(obj, data_model)
            for obj in self._query().bm25(
                query, properties, limit, autocut, return_metadata, return_properties
            )
        ]

    def bm25_options(
        self,
        query: str,
        returns: ReturnValues,
        options: Optional[BM25Options] = None,
        data_model: Optional[Type[Properties]] = None,
    ) -> List[_Object[Properties]]:
        if options is None:
            options = BM25Options()
        return [
            self.__result_to_object(obj, data_model)
            for obj in self._query().bm25(
                query,
                options.properties,
                options.limit,
                options.autocut,
                returns.metadata,
                returns.properties,
            )
        ]

    def near_vector_flat(
        self,
        vector: List[float],
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        autocut: Optional[int] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
        data_model: Optional[Type[Properties]] = None,
    ) -> List[_Object[Properties]]:
        return [
            self.__result_to_object(obj, data_model)
            for obj in self._query().near_vector(
                vector, certainty, distance, autocut, return_metadata, return_properties
            )
        ]

    def near_vector_options(
        self,
        vector: List[float],
        returns: ReturnValues,
        options: Optional[NearVectorOptions] = None,
        data_model: Optional[Type[Properties]] = None,
    ) -> List[_Object[Properties]]:
        if options is None:
            options = NearVectorOptions()
        return [
            self.__result_to_object(obj, data_model)
            for obj in self._query().near_vector(
                vector,
                options.certainty,
                options.distance,
                options.autocut,
                returns.metadata,
                returns.properties,
            )
        ]

    def near_object_flat(
        self,
        obj: UUID,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        autocut: Optional[int] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
        data_model: Optional[Type[Properties]] = None,
    ) -> List[_Object[Properties]]:
        return [
            self.__result_to_object(obj, data_model)
            for obj in self._query().near_object(
                obj, certainty, distance, autocut, return_metadata, return_properties
            )
        ]

    def near_object_options(
        self,
        obj: UUID,
        returns: ReturnValues,
        options: Optional[NearObjectOptions] = None,
        data_model: Optional[Type[Properties]] = None,
    ) -> List[_Object[Properties]]:
        if options is None:
            options = NearObjectOptions()
        return [
            self.__result_to_object(obj, data_model)
            for obj in self._query().near_object(
                obj,
                options.certainty,
                options.distance,
                options.autocut,
                returns.metadata,
                returns.properties,
            )
        ]

    def near_text_flat(
        self,
        query: Union[List[str], str],
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        move_to: Optional[Move] = None,
        move_away: Optional[Move] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
        data_model: Optional[Type[Properties]] = None,
    ) -> List[_Object[Properties]]:
        return [
            self.__result_to_object(obj, data_model)
            for obj in self._query().near_text(
                near_text=query,
                certainty=certainty,
                distance=distance,
                move_to=move_to,
                move_away=move_away,
                autocut=autocut,
                filters=filters,
                return_metadata=return_metadata,
                return_properties=return_properties,
            )
        ]

    def near_text_options(
        self,
        query: Union[List[str], str],
        returns: ReturnValues,
        options: Optional[NearTextOptions] = None,
        data_model: Optional[Type[Properties]] = None,
    ) -> List[_Object[Properties]]:
        if options is None:
            options = NearObjectOptions()

        return [
            self.__result_to_object(obj, data_model)
            for obj in self._query().near_text(
                near_text=query,
                certainty=options.certainty,
                distance=options.distance,
                move_to=options.move_to,
                move_away=options.move_away,
                autocut=options.autocut,
                filters=options.filters,
                return_metadata=returns.metadata,
                return_properties=returns.properties,
            )
        ]

    def near_image_flat(
        self,
        image: str,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
        data_model: Optional[Type[Properties]] = None,
    ) -> List[_Object[Properties]]:

        return [
            self.__result_to_object(obj, data_model)
            for obj in self._query().near_image(
                image=image,
                certainty=certainty,
                distance=distance,
                filters=filters,
                autocut=autocut,
                return_metadata=return_metadata,
                return_properties=return_properties,
            )
        ]

    def near_image_options(
        self,
        image: str,
        returns: ReturnValues,
        options: Optional[NearImageOptions] = None,
        filters: Optional[_Filters] = None,
        data_model: Optional[Type[Properties]] = None,
    ) -> List[_Object[Properties]]:
        if options is None:
            options = NearObjectOptions()

        return [
            self.__result_to_object(obj, data_model)
            for obj in self._query().near_image(
                image=image,
                certainty=options.certainty,
                distance=options.distance,
                filters=filters,
                autocut=options.autocut,
                return_metadata=returns.metadata,
                return_properties=returns.properties,
            )
        ]

    def near_audio_flat(
        self,
        audio: str,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
        data_model: Optional[Type[Properties]] = None,
    ) -> List[_Object[Properties]]:

        return [
            self.__result_to_object(obj, data_model)
            for obj in self._query().near_audio(
                audio=audio,
                certainty=certainty,
                distance=distance,
                filters=filters,
                autocut=autocut,
                return_metadata=return_metadata,
                return_properties=return_properties,
            )
        ]

    def near_audio_options(
        self,
        audio: str,
        returns: ReturnValues,
        options: Optional[NearAudioOptions] = None,
        filters: Optional[_Filters] = None,
        data_model: Optional[Type[Properties]] = None,
    ) -> List[_Object[Properties]]:
        if options is None:
            options = NearObjectOptions()

        return [
            self.__result_to_object(obj, data_model)
            for obj in self._query().near_image(
                image=audio,
                certainty=options.certainty,
                distance=options.distance,
                filters=filters,
                autocut=options.autocut,
                return_metadata=returns.metadata,
                return_properties=returns.properties,
            )
        ]

    def near_video_flat(
        self,
        video: str,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
        data_model: Optional[Type[Properties]] = None,
    ) -> List[_Object[Properties]]:

        return [
            self.__result_to_object(obj, data_model)
            for obj in self._query().near_video(
                video=video,
                certainty=certainty,
                distance=distance,
                filters=filters,
                autocut=autocut,
                return_metadata=return_metadata,
                return_properties=return_properties,
            )
        ]

    def near_video_options(
        self,
        video: str,
        returns: ReturnValues,
        options: Optional[NearVideoOptions] = None,
        filters: Optional[_Filters] = None,
        data_model: Optional[Type[Properties]] = None,
    ) -> List[_Object[Properties]]:
        if options is None:
            options = NearObjectOptions()

        return [
            self.__result_to_object(obj, data_model)
            for obj in self._query().near_video(
                video=video,
                certainty=options.certainty,
                distance=options.distance,
                filters=filters,
                autocut=options.autocut,
                return_metadata=returns.metadata,
                return_properties=returns.properties,
            )
        ]


class _GrpcCollectionModel(Generic[Model], _Grpc):
    def __init__(
        self, connection: Connection, name: str, model: Type[Model], tenant: Optional[str] = None
    ):
        super().__init__(connection, name, tenant)
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
                        properties=self.__parse_result(prop, referenced_property_type),
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
                limit, offset, after, filters, return_metadata, return_properties
            )
        ]

    def get_options(
        self,
        returns: ReturnValues,
        options: Optional[GetOptions],
        filters: Optional[_Filters] = None,
    ) -> List[_Object[Model]]:
        if options is None:
            options = GetOptions()
        return [
            self.__result_to_object(obj)
            for obj in self._query().get(
                options.limit,
                options.offset,
                options.after,
                filters,
                returns.metadata,
                returns.properties,
            )
        ]

    def hybrid_flat(
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
    ) -> List[_Object[Model]]:
        return [
            self.__result_to_object(obj)
            for obj in self._query().hybrid(
                query,
                alpha,
                vector,
                properties,
                fusion_type,
                limit,
                autocut,
                return_metadata,
                return_properties,
            )
        ]

    def hybrid_options(
        self,
        query: str,
        returns: ReturnValues,
        options: Optional[HybridOptions] = None,
    ) -> List[_Object[Model]]:
        if options is None:
            options = HybridOptions()
        return [
            self.__result_to_object(obj)
            for obj in self._query().hybrid(
                query,
                options.alpha,
                options.vector,
                options.properties,
                options.fusion_type,
                options.limit,
                options.autocut,
                returns.metadata,
                returns.properties,
            )
        ]

    def bm25_flat(
        self,
        query: str,
        properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        autocut: Optional[int] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[_Object[Model]]:
        return [
            self.__result_to_object(obj)
            for obj in self._query().bm25(
                query, properties, limit, autocut, return_metadata, return_properties
            )
        ]

    def bm25_options(
        self,
        query: str,
        returns: ReturnValues,
        options: Optional[BM25Options] = None,
    ) -> List[_Object[Model]]:
        if options is None:
            options = BM25Options()
        return [
            self.__result_to_object(obj)
            for obj in self._query().bm25(
                query,
                options.properties,
                options.limit,
                options.autocut,
                returns.metadata,
                returns.properties,
            )
        ]

    def near_vector_flat(
        self,
        vector: List[float],
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        autocut: Optional[int] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[_Object[Model]]:
        return [
            self.__result_to_object(obj)
            for obj in self._query().near_vector(
                vector, certainty, distance, autocut, return_metadata, return_properties
            )
        ]

    def near_vector_options(
        self,
        vector: List[float],
        returns: ReturnValues,
        options: Optional[NearVectorOptions] = None,
    ) -> List[_Object[Model]]:
        if options is None:
            options = NearVectorOptions()
        return [
            self.__result_to_object(obj)
            for obj in self._query().near_vector(
                vector,
                options.certainty,
                options.distance,
                options.autocut,
                returns.metadata,
                returns.properties,
            )
        ]

    def near_object_flat(
        self,
        obj: UUID,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        autocut: Optional[int] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[_Object[Model]]:
        return [
            self.__result_to_object(obj)
            for obj in self._query().near_object(
                obj, certainty, distance, autocut, return_metadata, return_properties
            )
        ]

    def near_object_options(
        self,
        obj: UUID,
        returns: ReturnValues,
        options: Optional[NearObjectOptions] = None,
    ) -> List[_Object[Model]]:
        if options is None:
            options = NearObjectOptions()
        return [
            self.__result_to_object(obj)
            for obj in self._query().near_object(
                obj,
                options.certainty,
                options.distance,
                options.autocut,
                returns.metadata,
                returns.properties,
            )
        ]

    def near_text_flat(
        self,
        query: Union[List[str], str],
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        move_to: Optional[Move] = None,
        move_away: Optional[Move] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[_Object[Properties]]:
        return [
            self.__result_to_object(obj)
            for obj in self._query().near_text(
                near_text=query,
                certainty=certainty,
                distance=distance,
                move_to=move_to,
                move_away=move_away,
                autocut=autocut,
                filters=filters,
                return_metadata=return_metadata,
                return_properties=return_properties,
            )
        ]

    def near_text_options(
        self,
        query: Union[List[str], str],
        returns: ReturnValues,
        options: Optional[NearTextOptions] = None,
    ) -> List[_Object[Properties]]:
        if options is None:
            options = NearObjectOptions()

        return [
            self.__result_to_object(obj)
            for obj in self._query().near_text(
                near_text=query,
                certainty=options.certainty,
                distance=options.distance,
                move_to=options.move_to,
                move_away=options.move_away,
                autocut=options.autocut,
                filters=options.filters,
                return_metadata=returns.metadata,
                return_properties=returns.properties,
            )
        ]

    def near_image_flat(
        self,
        image: str,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[_Object[Properties]]:

        return [
            self.__result_to_object(obj)
            for obj in self._query().near_image(
                image=image,
                certainty=certainty,
                distance=distance,
                filters=filters,
                autocut=autocut,
                return_metadata=return_metadata,
                return_properties=return_properties,
            )
        ]

    def near_image_options(
        self,
        image: str,
        returns: ReturnValues,
        options: Optional[NearImageOptions] = None,
        filters: Optional[_Filters] = None,
    ) -> List[_Object[Properties]]:
        if options is None:
            options = NearObjectOptions()

        return [
            self.__result_to_object(obj)
            for obj in self._query().near_image(
                image=image,
                certainty=options.certainty,
                distance=options.distance,
                filters=filters,
                autocut=options.autocut,
                return_metadata=returns.metadata,
                return_properties=returns.properties,
            )
        ]

    def near_audio_flat(
        self,
        audio: str,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[_Object[Properties]]:

        return [
            self.__result_to_object(obj)
            for obj in self._query().near_audio(
                audio=audio,
                certainty=certainty,
                distance=distance,
                filters=filters,
                autocut=autocut,
                return_metadata=return_metadata,
                return_properties=return_properties,
            )
        ]

    def near_audio_options(
        self,
        audio: str,
        returns: ReturnValues,
        options: Optional[NearAudioOptions] = None,
        filters: Optional[_Filters] = None,
    ) -> List[_Object[Properties]]:
        if options is None:
            options = NearObjectOptions()

        return [
            self.__result_to_object(obj)
            for obj in self._query().near_image(
                image=audio,
                certainty=options.certainty,
                distance=options.distance,
                filters=filters,
                autocut=options.autocut,
                return_metadata=returns.metadata,
                return_properties=returns.properties,
            )
        ]

    def near_video_flat(
        self,
        video: str,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[_Object[Properties]]:

        return [
            self.__result_to_object(obj)
            for obj in self._query().near_video(
                video=video,
                certainty=certainty,
                distance=distance,
                filters=filters,
                autocut=autocut,
                return_metadata=return_metadata,
                return_properties=return_properties,
            )
        ]

    def near_video_options(
        self,
        video: str,
        returns: ReturnValues,
        options: Optional[NearVideoOptions] = None,
        filters: Optional[_Filters] = None,
    ) -> List[_Object[Properties]]:
        if options is None:
            options = NearObjectOptions()

        return [
            self.__result_to_object(obj)
            for obj in self._query().near_video(
                video=video,
                certainty=options.certainty,
                distance=options.distance,
                filters=filters,
                autocut=options.autocut,
                return_metadata=returns.metadata,
                return_properties=returns.properties,
            )
        ]
