import uuid as uuid_lib
from dataclasses import dataclass
from typing import (
    Awaitable,
    Dict,
    List,
    Literal,
    Optional,
    Sequence,
    Set,
    TypeVar,
    Union,
    cast,
)

from grpc.aio import AioRpcError  # type: ignore
from typing_extensions import TypeAlias

from weaviate.collections.classes.config import ConsistencyLevel
from weaviate.collections.classes.filters import _Filters
from weaviate.collections.classes.grpc import (
    HybridFusion,
    _QueryReferenceMultiTarget,
    _MetadataQuery,
    HybridVectorType,
    Move,
    QueryNested,
    _QueryReference,
    PROPERTIES,
    PROPERTY,
    REFERENCE,
    REFERENCES,
    _Sorting,
    Rerank,
    TargetVectorJoinType,
    NearVectorInputType,
)
from weaviate.collections.classes.internal import (
    _Generative,
    _GroupBy,
)
from weaviate.collections.filters import _FilterToGRPC
from weaviate.collections.grpc.retry import _Retry
from weaviate.collections.grpc.shared import _BaseGRPC, PERMISSION_DENIED
from weaviate.connect import ConnectionV4
from weaviate.exceptions import (
    InsufficientPermissionsError,
    WeaviateQueryError,
    WeaviateRetryError,
)
from weaviate.proto.v1 import base_search_pb2, search_get_pb2
from weaviate.types import NUMBER, UUID
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
        validate_arguments: bool,
    ):
        super().__init__(connection, consistency_level, validate_arguments)
        self._name: str = name
        self._tenant = tenant

    def get(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[_MetadataQuery] = None,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: Optional[REFERENCES] = None,
        generative: Optional[_Generative] = None,
        rerank: Optional[Rerank] = None,
    ) -> Awaitable[search_get_pb2.SearchReply]:
        if self._validate_arguments:
            _validate_input(_ValidateArgument([_Sorting, None], "sort", sort))

        if sort is not None:
            sort_by: Optional[List[search_get_pb2.SortBy]] = [
                search_get_pb2.SortBy(ascending=sort.ascending, path=[sort.prop])
                for sort in sort.sorts
            ]
        else:
            sort_by = None

        request = self.__create_request(
            after=after,
            limit=limit,
            offset=offset,
            filters=filters,
            metadata=return_metadata,
            return_properties=return_properties,
            return_references=return_references,
            generative=generative,
            rerank=rerank,
            sort_by=sort_by,
        )

        return self.__call(request)

    def hybrid(
        self,
        query: Optional[str],
        alpha: Optional[float] = None,
        vector: Optional[HybridVectorType] = None,
        properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        distance: Optional[NUMBER] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Optional[_GroupBy] = None,
        return_metadata: Optional[_MetadataQuery] = None,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: Optional[REFERENCES] = None,
        generative: Optional[_Generative] = None,
        rerank: Optional[Rerank] = None,
        target_vector: Optional[TargetVectorJoinType] = None,
    ) -> Awaitable[search_get_pb2.SearchReply]:
        request = self.__create_request(
            limit=limit,
            offset=offset,
            filters=filters,
            group_by=group_by,
            metadata=return_metadata,
            return_properties=return_properties,
            return_references=return_references,
            generative=generative,
            rerank=rerank,
            autocut=autocut,
            hybrid_search=self._parse_hybrid(
                query,
                alpha,
                vector,
                properties,
                fusion_type,
                distance,
                target_vector,
            ),
        )
        return self.__call(request)

    def bm25(
        self,
        query: Optional[str],
        properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Optional[_GroupBy] = None,
        return_metadata: Optional[_MetadataQuery] = None,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: Optional[REFERENCES] = None,
        generative: Optional[_Generative] = None,
        rerank: Optional[Rerank] = None,
    ) -> Awaitable[search_get_pb2.SearchReply]:
        if self._validate_arguments:
            _validate_input(
                [
                    _ValidateArgument([None, str], "query", query),
                    _ValidateArgument([List, None], "properties", properties),
                ]
            )

        request = self.__create_request(
            limit=limit,
            offset=offset,
            filters=filters,
            group_by=group_by,
            metadata=return_metadata,
            return_properties=return_properties,
            return_references=return_references,
            generative=generative,
            rerank=rerank,
            autocut=autocut,
            bm25=(
                base_search_pb2.BM25(
                    query=query, properties=properties if properties is not None else []
                )
                if query is not None
                else None
            ),
        )
        return self.__call(request)

    def near_vector(
        self,
        near_vector: NearVectorInputType,
        certainty: Optional[NUMBER] = None,
        distance: Optional[NUMBER] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        autocut: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Optional[_GroupBy] = None,
        generative: Optional[_Generative] = None,
        rerank: Optional[Rerank] = None,
        target_vector: Optional[TargetVectorJoinType] = None,
        return_metadata: Optional[_MetadataQuery] = None,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: Optional[REFERENCES] = None,
    ) -> Awaitable[search_get_pb2.SearchReply]:
        request = self.__create_request(
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
            near_vector=self._parse_near_vector(
                near_vector, certainty, distance, target_vector=target_vector
            ),
        )
        return self.__call(request)

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
        target_vector: Optional[TargetVectorJoinType] = None,
        return_metadata: Optional[_MetadataQuery] = None,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: Optional[REFERENCES] = None,
    ) -> Awaitable[search_get_pb2.SearchReply]:
        request = self.__create_request(
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
            near_object=self._parse_near_object(near_object, certainty, distance, target_vector),
        )
        return self.__call(request)

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
        target_vector: Optional[TargetVectorJoinType] = None,
        return_metadata: Optional[_MetadataQuery] = None,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: Optional[REFERENCES] = None,
    ) -> Awaitable[search_get_pb2.SearchReply]:
        request = self.__create_request(
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
            near_text=self._parse_near_text(
                near_text,
                certainty,
                distance,
                move_away=move_away,
                move_to=move_to,
                target_vector=target_vector,
            ),
        )
        return self.__call(request)

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
        target_vector: Optional[TargetVectorJoinType] = None,
        return_metadata: Optional[_MetadataQuery] = None,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: Optional[REFERENCES] = None,
    ) -> Awaitable[search_get_pb2.SearchReply]:
        request = self.__create_request(
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
            **self._parse_media(
                media,
                type_,
                certainty,
                distance,
                target_vector,
            ),
        )
        return self.__call(request)

    def __create_request(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        metadata: Optional[_MetadataQuery] = None,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: Optional[REFERENCES] = None,
        generative: Optional[_Generative] = None,
        rerank: Optional[Rerank] = None,
        autocut: Optional[int] = None,
        group_by: Optional[_GroupBy] = None,
        near_vector: Optional[base_search_pb2.NearVector] = None,
        sort_by: Optional[Sequence[search_get_pb2.SortBy]] = None,
        hybrid_search: Optional[base_search_pb2.Hybrid] = None,
        bm25: Optional[base_search_pb2.BM25] = None,
        near_object: Optional[base_search_pb2.NearObject] = None,
        near_text: Optional[base_search_pb2.NearTextSearch] = None,
        near_audio: Optional[base_search_pb2.NearAudioSearch] = None,
        near_depth: Optional[base_search_pb2.NearDepthSearch] = None,
        near_image: Optional[base_search_pb2.NearImageSearch] = None,
        near_imu: Optional[base_search_pb2.NearIMUSearch] = None,
        near_thermal: Optional[base_search_pb2.NearThermalSearch] = None,
        near_video: Optional[base_search_pb2.NearVideoSearch] = None,
    ) -> search_get_pb2.SearchRequest:
        if self._validate_arguments:
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
                        [str, bool, QueryNested, Sequence, None],
                        "return_properties",
                        return_properties,
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

        if return_references is not None:
            return_references_parsed: Optional[Set[REFERENCE]] = self.__convert_to_set(
                return_references
            )
        else:
            return_references_parsed = None

        return_properties_parsed = self.__parse_return_properties(return_properties)

        return search_get_pb2.SearchRequest(
            uses_123_api=True,
            uses_125_api=self._connection._weaviate_version.is_at_least(1, 25, 0),
            collection=self._name,
            limit=limit,
            offset=offset,
            after=str(after) if after is not None else "",
            autocut=autocut,
            properties=self._translate_properties_from_python_to_grpc(
                return_properties_parsed, return_references_parsed
            ),
            metadata=(self._metadata_to_grpc(metadata) if metadata is not None else None),
            consistency_level=self._consistency_level,
            tenant=self._tenant,
            filters=_FilterToGRPC.convert(filters),
            generative=generative.to_grpc() if generative is not None else None,
            group_by=group_by.to_grpc() if group_by is not None else None,
            rerank=(
                search_get_pb2.Rerank(property=rerank.prop, query=rerank.query)
                if rerank is not None
                else None
            ),
            near_vector=near_vector,
            sort_by=sort_by,
            hybrid_search=hybrid_search,
            bm25_search=bm25,
            near_object=near_object,
            near_text=near_text,
            near_audio=near_audio,
            near_depth=near_depth,
            near_image=near_image,
            near_imu=near_imu,
            near_thermal=near_thermal,
            near_video=near_video,
        )

    async def __call(self, request: search_get_pb2.SearchRequest) -> search_get_pb2.SearchReply:
        try:
            assert self._connection.grpc_stub is not None
            res = await _Retry(4).with_exponential_backoff(
                0,
                f"Searching in collection {request.collection}",
                self._connection.grpc_stub.Search,
                request,
                metadata=self._connection.grpc_headers(),
                timeout=self._connection.timeout_config.query,
            )
            return cast(search_get_pb2.SearchReply, res)
        except AioRpcError as e:
            if e.code().name == PERMISSION_DENIED:
                raise InsufficientPermissionsError(e)
            raise WeaviateQueryError(str(e), "GRPC search")  # pyright: ignore
        except WeaviateRetryError as e:
            raise WeaviateQueryError(str(e), "GRPC search")  # pyright: ignore

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
            vectors=metadata.vectors,
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

    def __parse_return_properties(
        self, props: Union[PROPERTIES, bool, None]
    ) -> Optional[Set[PROPERTY]]:
        if props is None or props is True:
            return None
        return self.__convert_to_set([] if props is False else props)

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
                            self.__parse_return_properties(ref.return_properties),
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
