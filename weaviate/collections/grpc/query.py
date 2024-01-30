from dataclasses import dataclass
import struct
from typing import (
    Dict,
    List,
    Literal,
    Optional,
    Sequence,
    Set,
    Tuple,
    TypeVar,
    Union,
    cast,
)

from typing_extensions import TypeAlias

import grpc  # type: ignore
import uuid as uuid_lib

from weaviate.collections.classes.config import ConsistencyLevel

from weaviate.collections.classes.filters import _Filters
from weaviate.collections.classes.grpc import (
    HybridFusion,
    _QueryReferenceMultiTarget,
    _MetadataQuery,
    Move,
    QueryNested,
    _QueryReference,
    PROPERTIES,
    PROPERTY,
    REFERENCE,
    REFERENCES,
    _Sort,
    _Sorting,
    Rerank,
)
from weaviate.collections.classes.internal import _Generative, _GroupBy
from weaviate.collections.filters import _FilterToGRPC

from weaviate.collections.grpc.shared import _BaseGRPC

from weaviate.connect import ConnectionV4
from weaviate.exceptions import WeaviateQueryError, WeaviateInvalidInputError
from weaviate.types import NUMBER, UUID

from weaviate.proto.v1 import search_get_pb2

from weaviate.validator import _ValidateArgument, _validate_input


# Can be found in the google.protobuf.internal.well_known_types.pyi stub file but is defined explicitly here for clarity.
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
class _Move:
    force: float
    concepts: List[str]
    objects: List[uuid_lib.UUID]


A = TypeVar("A")


class _QueryGRPC(_BaseGRPC):
    def __init__(
        self,
        connection: ConnectionV4,
        name: str,
        tenant: Optional[str],
        consistency_level: Optional[ConsistencyLevel],
    ):
        super().__init__(connection, consistency_level)
        self._name: str = name
        self._tenant = tenant

        self._return_props: Optional[Set[PROPERTY]] = None
        self._metadata: Optional[_MetadataQuery] = None
        self._return_refs: Optional[Set[REFERENCE]] = None

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

        self._near_audio: Optional[str] = None
        self._near_depth: Optional[str] = None
        self._near_image: Optional[str] = None
        self._near_imu: Optional[str] = None
        self._near_thermal: Optional[str] = None
        self._near_video: Optional[str] = None

        self._generative: Optional[_Generative] = None
        self._rerank: Optional[Rerank] = None
        self._sort: Optional[List[_Sort]] = None

        self._group_by: Optional[_GroupBy] = None

        self._filters: Optional[_Filters] = None

    def __parse_sort(self, sort: Optional[_Sorting]) -> None:
        if sort is not None and not isinstance(sort, _Sorting):
            raise WeaviateInvalidInputError(
                f"sort must be of type weaviate.classes.query.Sorting, but got {type(sort)}"
            )
        if sort is None:
            self._sort = None
        else:
            self._sort = sort.sorts

    def __parse_common(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        metadata: Optional[_MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Optional[REFERENCES] = None,
        generative: Optional[_Generative] = None,
        rerank: Optional[Rerank] = None,
        autocut: Optional[int] = None,
        group_by: Optional[_GroupBy] = None,
    ) -> None:
        _validate_input(
            [
                _ValidateArgument([int, None], "limit", limit),
                _ValidateArgument([int, None], "offset", offset),
                _ValidateArgument([uuid_lib.UUID, str, None], "after", after),
                _ValidateArgument([_Filters, None], "filters", filters),
                _ValidateArgument([_MetadataQuery, None], "metadata", metadata),
                _ValidateArgument([_Generative, None], "generative", generative),
                _ValidateArgument([Rerank, None], "rerank", rerank),
                _ValidateArgument([int, None], "autocut", autocut),
                _ValidateArgument([_GroupBy, None], "group_by", group_by),
                _ValidateArgument(
                    [str, QueryNested, Sequence, None], "return_properties", return_properties
                ),
                _ValidateArgument(
                    [_QueryReference, Sequence, None], "return_references", return_references
                ),
            ]
        )
        if isinstance(return_properties, Sequence):
            for prop in return_properties:
                _validate_input(
                    _ValidateArgument(
                        expected=[str, QueryNested], name="return_properties", value=prop
                    )
                )

        if isinstance(return_references, Sequence):
            for ref in return_references:
                _validate_input(
                    _ValidateArgument(
                        expected=[_QueryReference], name="return_references", value=ref
                    )
                )

        self._limit = limit
        self._offset = offset
        self._after = after
        self._filters = filters
        self._metadata = metadata
        self._generative = generative
        self._rerank = rerank
        self._autocut = autocut
        self._group_by = group_by

        if return_references is not None:
            self._return_refs = self.__convert_to_set(return_references)
        if return_properties is not None:
            self._return_props = self.__convert_to_set(return_properties)

    def __parse_hybrid(
        self,
        query: str,
        alpha: Optional[NUMBER] = None,
        vector: Optional[List[float]] = None,
        properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
    ) -> None:
        if not isinstance(query, str):
            raise WeaviateInvalidInputError(f"query must be of type str, but got {type(query)}")
        if alpha is not None and not isinstance(alpha, float) and not isinstance(alpha, int):
            raise WeaviateInvalidInputError(
                f"alpha must be of type float or int, but got {type(alpha)}"
            )
        if vector is not None and not isinstance(vector, list):
            raise WeaviateInvalidInputError(
                f"vector must be of type List[float], but got {type(vector)}"
            )
        if properties is not None and not isinstance(properties, list):
            raise WeaviateInvalidInputError(
                f"properties must be of type List[str], but got {type(properties)}"
            )
        if fusion_type is not None and not isinstance(fusion_type, HybridFusion):
            raise WeaviateInvalidInputError(
                f"fusion_type must be of type weaviate.classes.query.HybridFusion, but got {type(fusion_type)}."
            )
        self._hybrid_query = query
        self._hybrid_alpha = float(alpha) if alpha is not None else None
        self._hybrid_vector = vector
        self._hybrid_properties = properties
        self._hybrid_fusion_type = (
            search_get_pb2.Hybrid.FusionType.Value(fusion_type.value)
            if fusion_type is not None
            else None
        )

    def __parse_bm25(
        self,
        query: str,
        properties: Optional[List[str]] = None,
    ) -> None:
        if not isinstance(query, str):
            raise WeaviateInvalidInputError(f"query must be of type str, but got {type(query)}")
        if properties is not None and not isinstance(properties, list):
            raise WeaviateInvalidInputError(
                f"properties must be of type List[str], but got {type(properties)}"
            )
        self._bm25_query = query
        self._bm25_properties = properties

    def __parse_near_options(
        self,
        certainty: Optional[NUMBER] = None,
        distance: Optional[NUMBER] = None,
    ) -> None:
        if (
            certainty is not None
            and not isinstance(certainty, float)
            and not isinstance(certainty, int)
        ):
            raise WeaviateInvalidInputError(
                f"certainty must be of type float or int, but got {type(certainty)}"
            )
        if (
            distance is not None
            and not isinstance(distance, float)
            and not isinstance(distance, int)
        ):
            raise WeaviateInvalidInputError(
                f"distance must be of type float or int, but got {type(distance)}"
            )
        self._near_certainty = float(certainty) if certainty is not None else None
        self._near_distance = float(distance) if distance is not None else None

    def get(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[_MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Optional[REFERENCES] = None,
        generative: Optional[_Generative] = None,
        rerank: Optional[Rerank] = None,
    ) -> search_get_pb2.SearchReply:
        self.__parse_common(
            limit=limit,
            offset=offset,
            after=after,
            filters=filters,
            metadata=return_metadata,
            return_properties=return_properties,
            return_references=return_references,
            generative=generative,
            rerank=rerank,
        )
        self.__parse_sort(sort)
        return self.__call()

    def hybrid(
        self,
        query: str,
        alpha: Optional[float] = None,
        vector: Optional[List[float]] = None,
        properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[_MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Optional[REFERENCES] = None,
        generative: Optional[_Generative] = None,
        rerank: Optional[Rerank] = None,
    ) -> search_get_pb2.SearchReply:
        self.__parse_hybrid(query, alpha, vector, properties, fusion_type)
        self.__parse_common(
            limit=limit,
            offset=offset,
            filters=filters,
            metadata=return_metadata,
            return_properties=return_properties,
            return_references=return_references,
            generative=generative,
            rerank=rerank,
            autocut=autocut,
        )
        return self.__call()

    def bm25(
        self,
        query: str,
        properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        return_metadata: Optional[_MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Optional[REFERENCES] = None,
        generative: Optional[_Generative] = None,
        rerank: Optional[Rerank] = None,
    ) -> search_get_pb2.SearchReply:
        self.__parse_bm25(query, properties)
        self.__parse_common(
            limit=limit,
            offset=offset,
            filters=filters,
            metadata=return_metadata,
            return_properties=return_properties,
            return_references=return_references,
            generative=generative,
            rerank=rerank,
            autocut=autocut,
        )
        return self.__call()

    def near_vector(
        self,
        near_vector: List[float],
        certainty: Optional[NUMBER] = None,
        distance: Optional[NUMBER] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Optional[_GroupBy] = None,
        generative: Optional[_Generative] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[_MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Optional[REFERENCES] = None,
    ) -> search_get_pb2.SearchReply:
        if not isinstance(near_vector, list):
            raise WeaviateInvalidInputError(
                f"near_vector must be of type List[float], but got {type(near_vector)}"
            )
        self._near_vector_vec = near_vector
        self.__parse_near_options(certainty, distance)
        self.__parse_common(
            limit=limit,
            offset=offset,
            filters=filters,
            metadata=return_metadata,
            return_properties=return_properties,
            return_references=return_references,
            generative=generative,
            rerank=rerank,
            autocut=autocut,
            group_by=group_by,
        )
        return self.__call()

    def near_object(
        self,
        near_object: UUID,
        certainty: Optional[NUMBER] = None,
        distance: Optional[NUMBER] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Optional[_GroupBy] = None,
        generative: Optional[_Generative] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[_MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Optional[REFERENCES] = None,
    ) -> search_get_pb2.SearchReply:
        if not isinstance(near_object, str) and not isinstance(near_object, uuid_lib.UUID):
            raise WeaviateInvalidInputError(
                f"near_object must be of type str or uuid.UUID, but got {type(near_object)}"
            )
        self._near_object_obj = near_object
        self.__parse_near_options(certainty, distance)
        self.__parse_common(
            limit=limit,
            offset=offset,
            filters=filters,
            metadata=return_metadata,
            return_properties=return_properties,
            return_references=return_references,
            generative=generative,
            rerank=rerank,
            autocut=autocut,
            group_by=group_by,
        )
        return self.__call()

    def near_text(
        self,
        near_text: Union[List[str], str],
        certainty: Optional[NUMBER] = None,
        distance: Optional[NUMBER] = None,
        move_to: Optional[Move] = None,
        move_away: Optional[Move] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Optional[_GroupBy] = None,
        generative: Optional[_Generative] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[_MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Optional[REFERENCES] = None,
    ) -> search_get_pb2.SearchReply:
        if not isinstance(near_text, list) and not isinstance(near_text, str):
            raise WeaviateInvalidInputError(
                f"near_text must be of type List[str] or str, but got {type(near_text)}"
            )
        if move_away is not None and not isinstance(move_away, Move):
            raise WeaviateInvalidInputError(
                f"move_away must be of type Move, but got {type(move_away)}"
            )
        if move_to is not None and not isinstance(move_to, Move):
            raise WeaviateInvalidInputError(
                f"move_to must be of type Move, but got {type(move_to)}"
            )
        if isinstance(near_text, str):
            near_text = [near_text]
        self._near_text = near_text
        self.__parse_near_options(certainty, distance)
        self.__parse_common(
            limit=limit,
            offset=offset,
            filters=filters,
            metadata=return_metadata,
            return_properties=return_properties,
            return_references=return_references,
            generative=generative,
            rerank=rerank,
            autocut=autocut,
            group_by=group_by,
        )
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
        return self.__call()

    def near_media(
        self,
        media: str,
        type_: Literal["audio", "depth", "image", "imu", "thermal", "video"],
        certainty: Optional[NUMBER] = None,
        distance: Optional[NUMBER] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Optional[_GroupBy] = None,
        generative: Optional[_Generative] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[_MetadataQuery] = None,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Optional[REFERENCES] = None,
    ) -> search_get_pb2.SearchReply:
        if type_ == "audio":
            self._near_audio = media
        elif type_ == "depth":
            self._near_depth = media
        elif type_ == "image":
            self._near_image = media
        elif type_ == "imu":
            self._near_imu = media
        elif type_ == "thermal":
            self._near_thermal = media
        elif type_ == "video":
            self._near_video = media
        else:
            raise ValueError(
                f"type_ must be one of ['audio', 'depth', 'image', 'imu', 'thermal', 'video'], but got {type_}"
            )
        self.__parse_near_options(certainty, distance)
        self.__parse_common(
            limit=limit,
            offset=offset,
            filters=filters,
            metadata=return_metadata,
            return_properties=return_properties,
            return_references=return_references,
            generative=generative,
            rerank=rerank,
            autocut=autocut,
            group_by=group_by,
        )

        return self.__call()

    def __call(self) -> search_get_pb2.SearchReply:
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
            res: search_get_pb2.SearchReply  # According to PEP-0526
            res, _ = self._connection.grpc_stub.Search.with_call(
                search_get_pb2.SearchRequest(
                    uses_123_api=True,
                    collection=self._name,
                    limit=self._limit,
                    offset=self._offset,
                    after=str(self._after) if self._after is not None else "",
                    autocut=self._autocut,
                    near_vector=(
                        search_get_pb2.NearVector(
                            certainty=self._near_certainty,
                            distance=self._near_distance,
                            vector_bytes=struct.pack(
                                "{}f".format(len(self._near_vector_vec)), *self._near_vector_vec
                            ),
                        )
                        if self._near_vector_vec is not None
                        else None
                    ),
                    near_object=(
                        search_get_pb2.NearObject(
                            id=str(self._near_object_obj),
                            certainty=self._near_certainty,
                            distance=self._near_distance,
                        )
                        if self._near_object_obj is not None
                        else None
                    ),
                    properties=self._translate_properties_from_python_to_grpc(
                        self._return_props, self._return_refs
                    ),
                    metadata=(
                        self._metadata_to_grpc(self._metadata)
                        if self._metadata is not None
                        else None
                    ),
                    bm25_search=(
                        search_get_pb2.BM25(
                            properties=self._bm25_properties, query=self._bm25_query
                        )
                        if self._bm25_query is not None
                        else None
                    ),
                    hybrid_search=(
                        search_get_pb2.Hybrid(
                            properties=self._hybrid_properties,
                            query=self._hybrid_query,
                            alpha=self._hybrid_alpha,
                            fusion_type=cast(
                                search_get_pb2.Hybrid.FusionType, self._hybrid_fusion_type
                            ),
                            vector_bytes=(
                                struct.pack(
                                    "{}f".format(len(self._hybrid_vector)), *self._hybrid_vector
                                )
                                if self._hybrid_vector is not None
                                else None
                            ),
                        )
                        if self._hybrid_query is not None
                        else None
                    ),
                    tenant=self._tenant,
                    filters=_FilterToGRPC.convert(self._filters),
                    near_audio=(
                        search_get_pb2.NearAudioSearch(
                            audio=self._near_audio,
                            distance=self._near_distance,
                            certainty=self._near_certainty,
                        )
                        if self._near_audio is not None
                        else None
                    ),
                    near_depth=(
                        search_get_pb2.NearDepthSearch(
                            depth=self._near_depth,
                            distance=self._near_distance,
                            certainty=self._near_certainty,
                        )
                        if self._near_depth is not None
                        else None
                    ),
                    near_image=(
                        search_get_pb2.NearImageSearch(
                            image=self._near_image,
                            distance=self._near_distance,
                            certainty=self._near_certainty,
                        )
                        if self._near_image is not None
                        else None
                    ),
                    near_imu=(
                        search_get_pb2.NearIMUSearch(
                            imu=self._near_imu,
                            distance=self._near_distance,
                            certainty=self._near_certainty,
                        )
                        if self._near_imu is not None
                        else None
                    ),
                    near_text=(
                        search_get_pb2.NearTextSearch(
                            query=self._near_text,
                            certainty=self._near_certainty,
                            distance=self._near_distance,
                            move_to=self._near_text_move_to,
                            move_away=self._near_text_move_away,
                        )
                        if self._near_text is not None
                        else None
                    ),
                    near_thermal=(
                        search_get_pb2.NearThermalSearch(
                            thermal=self._near_thermal,
                            distance=self._near_distance,
                            certainty=self._near_certainty,
                        )
                        if self._near_thermal is not None
                        else None
                    ),
                    near_video=(
                        search_get_pb2.NearVideoSearch(
                            video=self._near_video,
                            distance=self._near_distance,
                            certainty=self._near_certainty,
                        )
                        if self._near_video is not None
                        else None
                    ),
                    consistency_level=self._consistency_level,
                    sort_by=(
                        [
                            search_get_pb2.SortBy(ascending=sort.ascending, path=[sort.prop])
                            for sort in self._sort
                        ]
                        if self._sort is not None
                        else None
                    ),
                    generative=self._generative.to_grpc() if self._generative is not None else None,
                    group_by=self._group_by.to_grpc() if self._group_by is not None else None,
                    rerank=(
                        search_get_pb2.Rerank(property=self._rerank.prop, query=self._rerank.query)
                        if self._rerank is not None
                        else None
                    ),
                ),
                metadata=metadata,
                timeout=self._connection.timeout_config.connect,
            )

            return res

        except grpc.RpcError as e:
            raise WeaviateQueryError(e.details(), "GRPC search")  # pyright: ignore

    def _metadata_to_grpc(self, metadata: _MetadataQuery) -> search_get_pb2.MetadataRequest:
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

    def __resolve_property(self, prop: QueryNested) -> search_get_pb2.ObjectPropertiesRequest:
        props = prop.properties if isinstance(prop.properties, list) else [prop.properties]
        return search_get_pb2.ObjectPropertiesRequest(
            prop_name=prop.name,
            primitive_properties=[p for p in props if isinstance(p, str)],
            object_properties=[
                self.__resolve_property(p) for p in props if isinstance(p, QueryNested)
            ],
        )

    def _translate_properties_from_python_to_grpc(
        self, properties: Optional[Set[PROPERTY]], references: Optional[Set[REFERENCE]]
    ) -> Optional[search_get_pb2.PropertiesRequest]:
        if properties is None and references is None:
            return None
        return search_get_pb2.PropertiesRequest(
            return_all_nonref_properties=properties is None,
            non_ref_properties=(
                None
                if properties is None
                else [prop for prop in properties if isinstance(prop, str)]
            ),
            ref_properties=(
                None
                if references is None
                else [
                    search_get_pb2.RefPropertiesRequest(
                        reference_property=ref.link_on,
                        properties=self._translate_properties_from_python_to_grpc(
                            (
                                None
                                if ref.return_properties is None
                                else self.__convert_to_set(ref.return_properties)
                            ),
                            (
                                None
                                if ref.return_references is None
                                else self.__convert_to_set(ref.return_references)
                            ),
                        ),
                        metadata=(
                            self._metadata_to_grpc(ref._return_metadata)
                            if ref._return_metadata is not None
                            else None
                        ),
                        target_collection=(
                            ref.target_collection
                            if isinstance(ref, _QueryReferenceMultiTarget)
                            else None
                        ),
                    )
                    for ref in references
                ]
            ),
            object_properties=(
                None
                if properties is None
                else [
                    self.__resolve_property(prop)
                    for prop in properties
                    if isinstance(prop, QueryNested)
                ]
            ),
        )

    @staticmethod
    def __convert_to_set(args: Union[A, Sequence[A]]) -> Set[A]:
        if isinstance(args, list):
            return set(args)
        else:
            return {cast(A, args)}
