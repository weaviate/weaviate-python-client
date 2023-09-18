import datetime
import sys
from dataclasses import dataclass
from typing import (
    Any,
    Dict,
    Set,
    List,
    Literal,
    Optional,
    Union,
    Tuple,
    Type,
    Generic,
    cast,
    overload,
)

from typing_extensions import TypeAlias

from weaviate.collection.classes.config import ConsistencyLevel
from weaviate.collection.extract_filters import FilterToGRPC
from weaviate.collection.grpc_shared import _BaseGRPC

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
    Generate,
    HybridFusion,
    LinkTo,
    LinkToMultiTarget,
    MetadataQuery,
    Move,
    PROPERTY,
    PROPERTIES,
    Sort,
    GroupBy,
)
from weaviate.collection.classes.internal import (
    _GroupByObject,
    _MetadataReturn,
    _Object,
    ReferenceFactory,
    _extract_property_type_from_annotated_reference,
    _extract_property_type_from_reference,
    _extract_properties_from_data_model,
    _GenerativeReturn,
    _QueryReturn,
    _GroupByResult,
    _GroupByReturn,
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
class GroupByResult:
    name: str
    min_distance: float
    max_distance: float
    number_of_objects: int
    objects: List[SearchResult]


@dataclass
class SearchResponse:
    # the name of these members must match the proto file
    results: List[SearchResult]
    generative_grouped_result: str
    group_by_results: List[GroupByResult]


@dataclass
class _Move:
    force: float
    concepts: List[str]
    objects: List[uuid_lib.UUID]


class _GRPC(_BaseGRPC):
    def __init__(
        self,
        connection: Connection,
        name: str,
        tenant: Optional[str],
        consistency_level: Optional[ConsistencyLevel],
        default_properties: Optional[PROPERTIES] = None,
    ):
        super().__init__(connection, consistency_level)
        self._name: str = name
        self._tenant = tenant

        if default_properties is not None:
            self._default_props: Set[PROPERTY] = self.__convert_properties_to_set(
                default_properties
            )
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

        self._sort: Optional[List[Sort]] = None

        self._group_by: Optional[GroupBy] = None

        self._filters: Optional[_Filters] = None

    def __parse_sort(self, sort: Optional[Union[Sort, List[Sort]]]) -> None:
        if sort is None:
            self._sort = None
        elif isinstance(sort, Sort):
            self._sort = [sort]
        else:
            self._sort = sort

    def get(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[Union[Sort, List[Sort]]] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
        generative_single: Optional[str] = None,
        generative_grouped: Optional[str] = None,
        generative_grouped_properties: Optional[List[str]] = None,
    ) -> SearchResponse:
        self._limit = limit
        self._offset = offset
        self._after = after
        self._filters = filters
        self._metadata = return_metadata
        self.__parse_sort(sort)
        self.__merge_default_and_return_properties(return_properties)
        self._generative_single = generative_single
        self._generative_grouped = generative_grouped
        self._generative_grouped_properties = generative_grouped_properties
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
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
        generative_single: Optional[str] = None,
        generative_grouped: Optional[str] = None,
        generative_grouped_properties: Optional[List[str]] = None,
    ) -> SearchResponse:
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
        self.__merge_default_and_return_properties(return_properties)

        self._generative_single = generative_single
        self._generative_grouped = generative_grouped
        self._generative_grouped_properties = generative_grouped_properties

        return self.__call()

    def bm25(
        self,
        query: str,
        properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
        generative_single: Optional[str] = None,
        generative_grouped: Optional[str] = None,
        generative_grouped_properties: Optional[List[str]] = None,
    ) -> SearchResponse:
        self._bm25_query = query
        self._bm25_properties = properties
        self._limit = limit
        self._autocut = autocut
        self._filters = filters
        self._metadata = return_metadata
        self.__merge_default_and_return_properties(return_properties)

        self._generative_single = generative_single
        self._generative_grouped = generative_grouped
        self._generative_grouped_properties = generative_grouped_properties

        return self.__call()

    def near_vector(
        self,
        near_vector: List[float],
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Optional[GroupBy] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> SearchResponse:
        self._near_vector_vec = near_vector
        self._near_certainty = certainty
        self._near_distance = distance
        self._autocut = autocut
        self._filters = filters
        self._metadata = return_metadata
        self._group_by = group_by
        self.__merge_default_and_return_properties(return_properties)

        return self.__call()

    def near_object(
        self,
        near_object: UUID,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Optional[GroupBy] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> SearchResponse:
        self._near_object_obj = near_object
        self._near_certainty = certainty
        self._near_distance = distance
        self._autocut = autocut
        self._filters = filters
        self._metadata = return_metadata
        self.__merge_default_and_return_properties(return_properties)

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
        group_by: Optional[GroupBy] = None,
        generate: Optional[Generate] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> SearchResponse:
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

        if generate is not None:
            self._generative_single = generate.single_prompt
            self._generative_grouped = generate.grouped_task
            self._generative_grouped_properties = generate.grouped_properties

        self._group_by = group_by
        self._metadata = return_metadata
        self.__merge_default_and_return_properties(return_properties)

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
    ) -> SearchResponse:
        self._near_image = image
        self._near_certainty = certainty
        self._near_distance = distance
        self._autocut = autocut
        self._filters = filters

        self._metadata = return_metadata
        self.__merge_default_and_return_properties(return_properties)

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
    ) -> SearchResponse:
        self._near_video = video
        self._near_certainty = certainty
        self._near_distance = distance
        self._autocut = autocut
        self._filters = filters

        self._metadata = return_metadata
        self.__merge_default_and_return_properties(return_properties)

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
    ) -> SearchResponse:
        self._near_audio = audio
        self._near_certainty = certainty
        self._near_distance = distance
        self._autocut = autocut
        self._filters = filters

        self._metadata = return_metadata
        self.__merge_default_and_return_properties(return_properties)

        return self.__call()

    def __call(self) -> SearchResponse:
        metadata: Optional[Tuple[Tuple[str, str], ...]] = None
        access_token = self._connection.get_current_bearer_token()

        metadata_list: List[Tuple[str, str]] = []
        if len(access_token) > 0:
            metadata_list.append(("authorization", access_token))

        if len(self._connection.additional_headers):
            for key, val in self._connection.additional_headers.items():
                if val is not None:
                    metadata_list.append((key.lower(), val))

        if len(metadata_list) > 0:
            metadata = tuple(metadata_list)

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
                    consistency_level=self._consistency_level,
                    sort_by=[
                        weaviate_pb2.SortBy(ascending=sort.ascending, path=[sort.prop])
                        for sort in self._sort
                    ]
                    if self._sort is not None
                    else None,
                    generative=weaviate_pb2.GenerativeSearch(
                        single_response_prompt=self._generative_single,
                        grouped_response_task=self._generative_grouped,
                        grouped_properties=self._generative_grouped_properties,
                    )
                    if self._generative_single is not None or self._generative_grouped is not None
                    else None,
                    group_by=weaviate_pb2.GroupBy(
                        path=[self._group_by.prop],
                        number_of_groups=self._group_by.number_of_groups,
                        objects_per_group=self._group_by.objects_per_group,
                    )
                    if self._group_by is not None
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

    def _convert_references_to_grpc(self, properties: Set[PROPERTY]) -> weaviate_pb2.Properties:
        return weaviate_pb2.Properties(
            non_ref_properties=[prop for prop in properties if isinstance(prop, str)],
            ref_properties=[
                weaviate_pb2.RefProperties(
                    reference_property=prop.link_on,
                    linked_properties=self._convert_references_to_grpc(
                        self.__convert_properties_to_set(prop.return_properties)
                    )
                    if prop.return_properties is not None
                    else None,
                    metadata=self._metadata_to_grpc(prop.return_metadata)
                    if prop.return_metadata is not None
                    else None,
                    which_collection=prop.target_collection
                    if isinstance(prop, LinkToMultiTarget)
                    else None,
                )
                for prop in properties
                if isinstance(prop, LinkTo)
            ],
        )

    def __merge_default_and_return_properties(
        self, return_properties: Optional[PROPERTIES]
    ) -> None:
        if return_properties is not None:
            self._default_props = self._default_props.union(
                self.__convert_properties_to_set(return_properties)
            )

    @staticmethod
    def __convert_properties_to_set(properties: PROPERTIES) -> Set[PROPERTY]:
        if isinstance(properties, list):
            return set(properties)
        else:
            return {properties}


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
                    assert get_origin(hint) is ReferenceFactory
                    referenced_property_type = _extract_property_type_from_reference(hint)
                result[ref_prop.prop_name] = ReferenceFactory._from(
                    [
                        _Object(
                            properties=self.__parse_result(prop, referenced_property_type),
                            metadata=self._extract_metadata_for_object(prop.metadata),
                        )
                        for prop in ref_prop.properties
                    ]
                )
            else:
                result[ref_prop.prop_name] = ReferenceFactory[Dict[str, Any]]._from(
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

    def __result_to_query_return(
        self,
        res: SearchResponse,
        type_: Optional[Type[Properties]],
    ) -> _QueryReturn[Properties]:
        objects = [self.__result_to_object(obj, type_=type_) for obj in res.results]
        return _QueryReturn[Properties](objects=objects)

    def __result_to_generative_return(
        self,
        res: SearchResponse,
        type_: Optional[Type[Properties]],
    ) -> _GenerativeReturn[Properties]:
        objects = [self.__result_to_object(obj, type_=type_) for obj in res.results]
        grouped_results = (
            res.generative_grouped_result if res.generative_grouped_result != "" else None
        )
        return _GenerativeReturn[Properties](
            objects=objects,
            generated=grouped_results,
        )

    def __result_to_groupby_return(
        self,
        res: SearchResponse,
        type_: Optional[Type[Properties]],
    ) -> _GroupByReturn[Properties]:
        groups = {
            group.name: self.__result_to_group(group, type_) for group in res.group_by_results
        }

        objects_group_by = [
            _GroupByObject[Properties](
                properties=obj.properties, metadata=obj.metadata, belongs_to_group=group.name
            )
            for group in groups.values()
            for obj in group.objects
        ]

        return _GroupByReturn[Properties](objects=objects_group_by, groups=groups)

    def __result_to_group(
        self, res: GroupByResult, type_: Optional[Type[Properties]]
    ) -> _GroupByResult[Properties]:
        return _GroupByResult[Properties](
            objects=[self.__result_to_object(obj, type_) for obj in res.objects],
            name=res.name,
            number_of_objects=res.number_of_objects,
            min_distance=res.min_distance,
            max_distance=res.max_distance,
        )

    def __determine_generic(
        self, type_: Union[PROPERTIES, Type[Properties], None]
    ) -> Tuple[Optional[PROPERTIES], Type[Properties]]:
        if (
            isinstance(type_, list)
            or isinstance(type_, str)
            or isinstance(type_, LinkTo)
            or type_ is None
        ):
            ret_properties = cast(Optional[PROPERTIES], type_)
            ret_type = cast(Type[Properties], Dict[str, Any])
        else:
            assert get_origin(type_) is not dict
            type_ = cast(Type[Properties], type_)
            ret_properties = _extract_properties_from_data_model(type_)
            ret_type = type_
        return ret_properties, ret_type

    @overload
    def get(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[Union[Sort, List[Sort]]] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
        generate: Literal[None] = None,
    ) -> _QueryReturn[Properties]:
        ...

    @overload
    def get(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[Union[Sort, List[Sort]]] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
        *,
        generate: Generate,
    ) -> _GenerativeReturn[Properties]:
        ...

    def get(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[Union[Sort, List[Sort]]] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
        generate: Optional[Generate] = None,
    ) -> Union[_QueryReturn[Properties], _GenerativeReturn[Properties]]:
        ret_properties, ret_type = self.__determine_generic(return_properties)
        res = self._query().get(
            limit=limit,
            offset=offset,
            after=after,
            filters=filters,
            sort=sort,
            return_metadata=return_metadata,
            return_properties=ret_properties,
            generative_single=generate.single_prompt if generate is not None else None,
            generative_grouped=generate.grouped_task if generate is not None else None,
            generative_grouped_properties=generate.grouped_properties
            if generate is not None
            else None,
        )
        if generate is None:
            return self.__result_to_query_return(res, ret_type)
        else:
            return self.__result_to_generative_return(res, ret_type)

    @overload
    def hybrid(
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
        generate: Literal[None] = None,
    ) -> _QueryReturn[Properties]:
        ...

    @overload
    def hybrid(
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
        *,
        generate: Generate,
    ) -> _GenerativeReturn[Properties]:
        ...

    def hybrid(
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
        generate: Optional[Generate] = None,
    ) -> Union[_QueryReturn[Properties], _GenerativeReturn[Properties]]:
        ret_properties, ret_type = self.__determine_generic(return_properties)
        res = self._query().hybrid(
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
            generative_single=generate.single_prompt if generate is not None else None,
            generative_grouped=generate.grouped_task if generate is not None else None,
            generative_grouped_properties=generate.grouped_properties
            if generate is not None
            else None,
        )
        if generate is None:
            return self.__result_to_query_return(res, ret_type)
        else:
            return self.__result_to_generative_return(res, ret_type)

    @overload
    def bm25(
        self,
        query: str,
        query_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        generate: Literal[None] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> _QueryReturn[Properties]:
        ...

    @overload
    def bm25(
        self,
        query: str,
        query_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        *,
        generate: Generate,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> _GenerativeReturn[Properties]:
        ...

    def bm25(
        self,
        query: str,
        query_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        generate: Optional[Generate] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> Union[_QueryReturn[Properties], _GenerativeReturn[Properties]]:
        ret_properties, ret_type = self.__determine_generic(return_properties)
        res = self._query().bm25(
            query=query,
            properties=query_properties,
            limit=limit,
            autocut=auto_limit,
            filters=filters,
            return_metadata=return_metadata,
            return_properties=ret_properties,
            generative_single=generate.single_prompt if generate is not None else None,
            generative_grouped=generate.grouped_task if generate is not None else None,
            generative_grouped_properties=generate.grouped_properties
            if generate is not None
            else None,
        )
        if generate is None:
            return self.__result_to_query_return(res, ret_type)
        else:
            return self.__result_to_generative_return(res, ret_type)

    def near_vector(
        self,
        near_vector: List[float],
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Optional[GroupBy] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> _QueryReturn[Properties]:
        ret_properties, ret_type = self.__determine_generic(return_properties)
        res = self._query().near_vector(
            near_vector=near_vector,
            certainty=certainty,
            distance=distance,
            autocut=auto_limit,
            filters=filters,
            group_by=group_by,
            return_metadata=return_metadata,
            return_properties=ret_properties,
        )
        return self.__result_to_query_return(res, ret_type)

    def near_object(
        self,
        near_object: UUID,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Optional[GroupBy] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> _QueryReturn[Properties]:
        ret_properties, ret_type = self.__determine_generic(return_properties)
        res = self._query().near_object(
            near_object=near_object,
            certainty=certainty,
            distance=distance,
            autocut=auto_limit,
            filters=filters,
            group_by=group_by,
            return_metadata=return_metadata,
            return_properties=ret_properties,
        )
        return self.__result_to_query_return(res, ret_type)

    @overload
    def near_text(
        self,
        query: Union[List[str], str],
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        move_to: Optional[Move] = None,
        move_away: Optional[Move] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Literal[None] = None,
        generate: Literal[None] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> _QueryReturn[Properties]:
        ...

    @overload
    def near_text(
        self,
        query: Union[List[str], str],
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        move_to: Optional[Move] = None,
        move_away: Optional[Move] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        *,
        group_by: Literal[None] = None,
        generate: Generate,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> _GenerativeReturn[Properties]:
        ...

    @overload
    def near_text(
        self,
        query: Union[List[str], str],
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        move_to: Optional[Move] = None,
        move_away: Optional[Move] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        *,
        group_by: GroupBy,
        generate: Literal[None] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> _GroupByReturn[Properties]:
        ...

    def near_text(
        self,
        query: Union[List[str], str],
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        move_to: Optional[Move] = None,
        move_away: Optional[Move] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Optional[GroupBy] = None,
        generate: Optional[Generate] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> Union[_QueryReturn[Properties], _GenerativeReturn[Properties], _GroupByReturn[Properties]]:
        if generate is not None and group_by is not None:
            raise ValueError("Cannot have groupby and generate")

        ret_properties, ret_type = self.__determine_generic(return_properties)
        res = self._query().near_text(
            near_text=query,
            certainty=certainty,
            distance=distance,
            move_to=move_to,
            move_away=move_away,
            autocut=auto_limit,
            filters=filters,
            group_by=group_by,
            generate=generate,
            return_metadata=return_metadata,
            return_properties=ret_properties,
        )
        if generate is None and group_by is None:
            return self.__result_to_query_return(res, ret_type)
        elif generate is not None:
            return self.__result_to_generative_return(res, ret_type)
        else:
            return self.__result_to_groupby_return(res, ret_type)

    def near_image(
        self,
        near_image: str,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> _QueryReturn[Properties]:
        ret_properties, ret_type = self.__determine_generic(return_properties)
        res = self._query().near_image(
            image=near_image,
            certainty=certainty,
            distance=distance,
            filters=filters,
            autocut=auto_limit,
            return_metadata=return_metadata,
            return_properties=ret_properties,
        )
        return self.__result_to_query_return(res, ret_type)

    def near_audio(
        self,
        near_audio: str,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> _QueryReturn[Properties]:
        ret_properties, ret_type = self.__determine_generic(return_properties)
        res = self._query().near_audio(
            audio=near_audio,
            certainty=certainty,
            distance=distance,
            filters=filters,
            autocut=auto_limit,
            return_metadata=return_metadata,
            return_properties=ret_properties,
        )
        return self.__result_to_query_return(res, ret_type)

    def near_video(
        self,
        near_video: str,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[Union[PROPERTIES, Type[Properties]]] = None,
    ) -> _QueryReturn[Properties]:
        ret_properties, ret_type = self.__determine_generic(return_properties)
        res = self._query().near_video(
            video=near_video,
            certainty=certainty,
            distance=distance,
            filters=filters,
            autocut=auto_limit,
            return_metadata=return_metadata,
            return_properties=ret_properties,
        )
        return self.__result_to_query_return(res, ret_type)


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

    def get(
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
            for obj in self._query()
            .get(
                limit=limit,
                offset=offset,
                after=after,
                filters=filters,
                return_metadata=return_metadata,
                return_properties=return_properties,
            )
            .results
        ]

    def hybrid(
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
            for obj in self._query()
            .hybrid(
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
            .results
        ]

    def bm25(
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
            for obj in self._query()
            .bm25(
                query=query,
                properties=query_properties,
                limit=limit,
                autocut=auto_limit,
                filters=filters,
                return_metadata=return_metadata,
                return_properties=return_properties,
            )
            .results
        ]

    def near_vector(
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
            for obj in self._query()
            .near_vector(
                near_vector=near_vector,
                certainty=certainty,
                distance=distance,
                autocut=auto_limit,
                filters=filters,
                return_metadata=return_metadata,
                return_properties=return_properties,
            )
            .results
        ]

    def near_object(
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
            for obj in self._query()
            .near_object(
                near_object=near_object,
                certainty=certainty,
                distance=distance,
                autocut=auto_limit,
                filters=filters,
                return_metadata=return_metadata,
                return_properties=return_properties,
            )
            .results
        ]

    def near_text(
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
            for obj in self._query()
            .near_text(
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
            .results
        ]

    def near_image(
        self,
        near_image: str,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[_Object[Model]]:
        return [
            self.__result_to_object(obj)
            for obj in self._query()
            .near_image(
                image=near_image,
                certainty=certainty,
                distance=distance,
                filters=filters,
                autocut=auto_limit,
                return_metadata=return_metadata,
                return_properties=return_properties,
            )
            .results
        ]

    def near_audio(
        self,
        near_audio: str,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[_Object[Model]]:
        return [
            self.__result_to_object(obj)
            for obj in self._query()
            .near_audio(
                audio=near_audio,
                certainty=certainty,
                distance=distance,
                filters=filters,
                autocut=auto_limit,
                return_metadata=return_metadata,
                return_properties=return_properties,
            )
            .results
        ]

    def near_video(
        self,
        near_video: str,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> List[_Object[Model]]:
        return [
            self.__result_to_object(obj)
            for obj in self._query()
            .near_video(
                video=near_video,
                certainty=certainty,
                distance=distance,
                filters=filters,
                autocut=auto_limit,
                return_metadata=return_metadata,
                return_properties=return_properties,
            )
            .results
        ]
