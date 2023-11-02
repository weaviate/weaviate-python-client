from dataclasses import dataclass
from typing import (
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Union,
    cast,
)

from typing_extensions import TypeAlias

import grpc  # type: ignore
import uuid as uuid_lib
from google.protobuf import struct_pb2

from weaviate.collections.classes.config import ConsistencyLevel

from weaviate.collections.classes.filters import _Filters
from weaviate.collections.classes.grpc import (
    HybridFusion,
    FromReference,
    FromReferenceMultiTarget,
    FromNested,
    MetadataQuery,
    Move,
    PROPERTIES,
    PROPERTY,
    Sort,
)
from weaviate.collections.classes.internal import _Generative, _GroupBy
from weaviate.collections.filters import _FilterToGRPC

from weaviate.collections.grpc.shared import _BaseGRPC

from weaviate.connect import Connection
from weaviate.exceptions import WeaviateQueryException
from weaviate.types import UUID

from weaviate.proto.v1 import search_get_pb2


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
class SearchResult:
    """Represents a single search result from Weaviate."""

    properties: search_get_pb2.PropertiesResult
    metadata: search_get_pb2.MetadataResult


@dataclass
class GroupByResult:
    """Represents a single group-by result from Weaviate."""

    name: str
    min_distance: float
    max_distance: float
    number_of_objects: int
    objects: List[SearchResult]


@dataclass
class SearchResponse:
    """Represents the response from a search request to Weaviate."""

    # the name of these members must match the proto file
    results: List[SearchResult]
    generative_grouped_result: str
    group_by_results: List[GroupByResult]


@dataclass
class _Move:
    force: float
    concepts: List[str]
    objects: List[uuid_lib.UUID]


class _QueryGRPC(_BaseGRPC):
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
        self._near_text_move_away: Optional[search_get_pb2.NearTextSearch.Move] = None
        self._near_text_move_to: Optional[search_get_pb2.NearTextSearch.Move] = None

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
            search_get_pb2.Hybrid.FusionType.Value(fusion_type.value)
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
        limit: Optional[int] = None,
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
        self._limit = limit
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
        limit: Optional[int] = None,
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
        self._limit = limit
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
        limit: Optional[int] = None,
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
        self._limit = limit
        self._autocut = autocut
        self._filters = filters
        if move_away is not None:
            self._near_text_move_away = search_get_pb2.NearTextSearch.Move(
                force=move_away.force,
                concepts=move_away._concepts_list,
                uuids=move_away._objects_list,
            )
        if move_to is not None:
            self._near_text_move_to = search_get_pb2.NearTextSearch.Move(
                force=move_to.force, concepts=move_to._concepts_list, uuids=move_to._objects_list
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
        limit: Optional[int] = None,
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
        self._limit = limit
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
        limit: Optional[int] = None,
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
        self._limit = limit
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
        limit: Optional[int] = None,
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
        self._limit = limit
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
                search_get_pb2.SearchRequest(
                    collection=self._name,
                    limit=self._limit,
                    offset=self._offset,
                    after=str(self._after) if self._after is not None else "",
                    autocut=self._autocut,
                    near_vector=search_get_pb2.NearVector(
                        vector=self._near_vector_vec,
                        certainty=self._near_certainty,
                        distance=self._near_distance,
                    )
                    if self._near_vector_vec is not None
                    else None,
                    near_object=search_get_pb2.NearObject(
                        id=str(self._near_object_obj),
                        certainty=self._near_certainty,
                        distance=self._near_distance,
                    )
                    if self._near_object_obj is not None
                    else None,
                    properties=self._translate_properties_from_python_to_grpc(self._default_props),
                    metadata=self._metadata_to_grpc(self._metadata)
                    if self._metadata is not None
                    else None,
                    bm25_search=search_get_pb2.BM25(
                        properties=self._bm25_properties, query=self._bm25_query
                    )
                    if self._bm25_query is not None
                    else None,
                    hybrid_search=search_get_pb2.Hybrid(
                        properties=self._hybrid_properties,
                        query=self._hybrid_query,
                        alpha=self._hybrid_alpha,
                        vector=self._hybrid_vector,
                        fusion_type=cast(
                            search_get_pb2.Hybrid.FusionType, self._hybrid_fusion_type
                        ),
                    )
                    if self._hybrid_query is not None
                    else None,
                    tenant=self._tenant,
                    filters=_FilterToGRPC.convert(self._filters),
                    near_text=search_get_pb2.NearTextSearch(
                        query=self._near_text,
                        certainty=self._near_certainty,
                        distance=self._near_distance,
                        move_to=self._near_text_move_to,
                        move_away=self._near_text_move_away,
                    )
                    if self._near_text is not None
                    else None,
                    near_image=search_get_pb2.NearImageSearch(
                        image=self._near_image,
                        distance=self._near_distance,
                        certainty=self._near_certainty,
                    )
                    if self._near_image is not None
                    else None,
                    near_video=search_get_pb2.NearVideoSearch(
                        video=self._near_video,
                        distance=self._near_distance,
                        certainty=self._near_certainty,
                    )
                    if self._near_video is not None
                    else None,
                    near_audio=search_get_pb2.NearAudioSearch(
                        audio=self._near_audio,
                        distance=self._near_distance,
                        certainty=self._near_certainty,
                    )
                    if self._near_audio is not None
                    else None,
                    consistency_level=self._consistency_level,
                    sort_by=[
                        search_get_pb2.SortBy(ascending=sort.ascending, path=[sort.prop])
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
            raise WeaviateQueryException(e.details())

    def _metadata_to_grpc(self, metadata: MetadataQuery) -> search_get_pb2.MetadataRequest:
        return search_get_pb2.MetadataRequest(
            uuid=metadata.uuid,
            vector=metadata.vector,
            creation_time_unix=metadata.creation_time_unix,
            last_update_time_unix=metadata.last_update_time_unix,
            distance=metadata.distance,
            certainty=metadata.certainty,
            explain_score=metadata.explain_score,
            score=metadata.score,
            is_consistent=metadata.is_consistent,
        )

    def _translate_properties_from_python_to_grpc(
        self, properties: Set[PROPERTY]
    ) -> search_get_pb2.PropertiesRequest:
        def resolve_property(prop: FromNested) -> search_get_pb2.ObjectPropertiesRequest:
            props = prop.properties if isinstance(prop.properties, list) else [prop.properties]
            return search_get_pb2.ObjectPropertiesRequest(
                prop_name=prop.name,
                primitive_properties=[p for p in props if isinstance(p, str)],
                object_properties=[resolve_property(p) for p in props if isinstance(p, FromNested)],
            )

        return search_get_pb2.PropertiesRequest(
            non_ref_properties=[prop for prop in properties if isinstance(prop, str)],
            ref_properties=[
                search_get_pb2.RefPropertiesRequest(
                    reference_property=prop.link_on,
                    properties=self._translate_properties_from_python_to_grpc(
                        self.__convert_properties_to_set(prop.return_properties)
                    )
                    if prop.return_properties is not None
                    else None,
                    metadata=self._metadata_to_grpc(prop.return_metadata)
                    if prop.return_metadata is not None
                    else None,
                    target_collection=prop.target_collection
                    if isinstance(prop, FromReferenceMultiTarget)
                    else None,
                )
                for prop in properties
                if isinstance(prop, FromReference)
            ],
            object_properties=[
                resolve_property(prop) for prop in properties if isinstance(prop, FromNested)
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
