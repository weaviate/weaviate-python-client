from dataclasses import dataclass
from typing import (
    Dict,
    Generic,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
    cast,
    get_type_hints,
)

from typing_extensions import TypeAlias

import grpc
import uuid as uuid_lib
from google.protobuf import struct_pb2

from weaviate.collection.classes.config import ConsistencyLevel

from weaviate.collection.classes.filters import _Filters
from weaviate.collection.classes.grpc import (
    HybridFusion,
    LinkTo,
    LinkToMultiTarget,
    MetadataQuery,
    Move,
    PROPERTIES,
    PROPERTY,
    Sort,
)
from weaviate.collection.classes.internal import _Generative, _GroupBy, _MetadataReturn, _Object
from weaviate.collection.classes.orm import Model
from weaviate.collection.classes.types import TProperties

from weaviate.collection.data import _DataCollection
from weaviate.collection.extract_filters import FilterToGRPC

from weaviate.collection.queries.base import _Grpc
from weaviate.collection.queries.bm25 import _BM25
from weaviate.collection.queries.fetch_objects import _FetchObjects
from weaviate.collection.queries.hybrid import _Hybrid
from weaviate.collection.queries.near_audio import _NearAudio
from weaviate.collection.queries.near_image import _NearImage
from weaviate.collection.queries.near_object import _NearObject
from weaviate.collection.queries.near_text import _NearText
from weaviate.collection.queries.near_vector import _NearVector
from weaviate.collection.queries.near_video import _NearVideo

from weaviate.collection.grpc_shared import _BaseGRPC

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

        self._generative: Optional[_Generative] = None

        self._sort: Optional[List[Sort]] = None

        self._group_by: Optional[_GroupBy] = None

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
        generative: Optional[_Generative] = None,
    ) -> SearchResponse:
        self._limit = limit
        self._offset = offset
        self._after = after
        self._filters = filters
        self._metadata = return_metadata
        self.__parse_sort(sort)
        self.__merge_default_and_return_properties(return_properties)
        self._generative = generative
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
        generative: Optional[_Generative] = None,
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

        self._generative = generative

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
        generative: Optional[_Generative] = None,
    ) -> SearchResponse:
        self._bm25_query = query
        self._bm25_properties = properties
        self._limit = limit
        self._autocut = autocut
        self._filters = filters
        self._metadata = return_metadata
        self.__merge_default_and_return_properties(return_properties)

        self._generative = generative

        return self.__call()

    def near_vector(
        self,
        near_vector: List[float],
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Optional[_GroupBy] = None,
        generative: Optional[_Generative] = None,
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
        self._generative = generative
        self.__merge_default_and_return_properties(return_properties)

        return self.__call()

    def near_object(
        self,
        near_object: UUID,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Optional[_GroupBy] = None,
        generative: Optional[_Generative] = None,
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
        self._group_by = group_by
        self._generative = generative
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
        group_by: Optional[_GroupBy] = None,
        generative: Optional[_Generative] = None,
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

        self._generative = generative

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
        group_by: Optional[_GroupBy] = None,
        generative: Optional[_Generative] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> SearchResponse:
        self._near_image = image
        self._near_certainty = certainty
        self._near_distance = distance
        self._autocut = autocut
        self._filters = filters
        self._group_by = group_by
        self._generative = generative

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
        group_by: Optional[_GroupBy] = None,
        generative: Optional[_Generative] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> SearchResponse:
        self._near_video = video
        self._near_certainty = certainty
        self._near_distance = distance
        self._autocut = autocut
        self._filters = filters
        self._group_by = group_by
        self._generative = generative

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
        group_by: Optional[_GroupBy] = None,
        generative: Optional[_Generative] = None,
        return_metadata: Optional[MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
    ) -> SearchResponse:
        self._near_audio = audio
        self._near_certainty = certainty
        self._near_distance = distance
        self._autocut = autocut
        self._filters = filters
        self._group_by = group_by
        self._generative = generative

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
                    generative=self._generative.to_grpc() if self._generative is not None else None,
                    group_by=self._group_by.to_grpc() if self._group_by is not None else None,
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


class _GrpcCollection(
    Generic[TProperties],
    _BM25,
    _FetchObjects,
    _Hybrid,
    _NearAudio,
    _NearImage,
    _NearObject,
    _NearText,
    _NearVector,
    _NearVideo,
):
    def __init__(
        self,
        connection: Connection,
        name: str,
        rest_query: _DataCollection[TProperties],
        consistency_level: Optional[ConsistencyLevel],
        tenant: Optional[str],
    ):
        super().__init__(connection, name, consistency_level, tenant)
        self.__data = rest_query

    def fetch_object_by_id(
        self, uuid: UUID, include_vector: bool = False
    ) -> Optional[_Object[TProperties]]:
        ret = self.__data._get_by_id(uuid=uuid, include_vector=include_vector)
        if ret is None:
            return ret
        return self.__data._json_to_object(ret)


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
