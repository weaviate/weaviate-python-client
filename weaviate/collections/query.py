from typing import (
    Any,
    Generic,
    List,
    Optional,
    Type,
    Union,
    cast,
    get_type_hints,
)

from weaviate.collections.classes.config import ConsistencyLevel

from weaviate.collections.classes.filters import _Filters
from weaviate.collections.classes.grpc import (
    HybridFusion,
    MetadataQuery,
    Move,
    PROPERTIES,
)
from weaviate.collections.classes.internal import _Object
from weaviate.collections.classes.orm import Model
from weaviate.collections.classes.types import TProperties

from weaviate.collections.data import _DataCollection

from weaviate.collections.grpc.query import SearchResult

from weaviate.collections.queries.base import _Grpc
from weaviate.collections.queries.bm25 import _BM25Generate, _BM25Query
from weaviate.collections.queries.fetch_objects import _FetchObjectsGenerate, _FetchObjectsQuery
from weaviate.collections.queries.hybrid import _HybridGenerate, _HybridQuery
from weaviate.collections.queries.near_audio import (
    _NearAudioGenerate,
    _NearAudioGroupBy,
    _NearAudioQuery,
)
from weaviate.collections.queries.near_image import (
    _NearImageGenerate,
    _NearImageGroupBy,
    _NearImageQuery,
)
from weaviate.collections.queries.near_object import (
    _NearObjectGenerate,
    _NearObjectGroupBy,
    _NearObjectQuery,
)
from weaviate.collections.queries.near_text import (
    _NearTextGenerate,
    _NearTextGroupBy,
    _NearTextQuery,
)
from weaviate.collections.queries.near_vector import (
    _NearVectorGenerate,
    _NearVectorGroupBy,
    _NearVectorQuery,
)
from weaviate.collections.queries.near_video import (
    _NearVideoGenerate,
    _NearVideoGroupBy,
    _NearVideoQuery,
)

from weaviate.connect import Connection
from weaviate.types import UUID

from weaviate.proto.v1 import search_get_pb2


class _QueryCollection(
    Generic[TProperties],
    _BM25Query[TProperties],
    _FetchObjectsQuery[TProperties],
    _HybridQuery,
    _NearAudioQuery,
    _NearImageQuery,
    _NearObjectQuery,
    _NearTextQuery,
    _NearVectorQuery,
    _NearVideoQuery,
):
    def __init__(
        self,
        connection: Connection,
        name: str,
        rest_query: _DataCollection[TProperties],
        consistency_level: Optional[ConsistencyLevel],
        tenant: Optional[str],
        type_: Optional[Type[TProperties]],
    ):
        super().__init__(connection, name, consistency_level, tenant, type_)
        self.__data = rest_query

    def fetch_object_by_id(
        self, uuid: UUID, include_vector: bool = False
    ) -> Optional[_Object[TProperties]]:
        """Retrieve an object from the server by its UUID.

        Arguments:
            `uuid`
                The UUID of the object to retrieve, REQUIRED.
            `include_vector`
                Whether to include the vector in the returned object.

        Raises:
            `weaviate.exceptions.WeaviateQueryException`:
                If the network connection to Weaviate fails.
            `weaviate.exceptions.WeaviateInsertInvalidPropertyError`:
                If a property is invalid. I.e., has name `id` or `vector`, which are reserved.
        """
        ret = self.__data._get_by_id(uuid=uuid, include_vector=include_vector)
        if ret is None:
            return ret
        return self.__data._json_to_object(ret)


class _GenerateCollection(
    _BM25Generate,
    _FetchObjectsGenerate,
    _HybridGenerate,
    _NearAudioGenerate,
    _NearImageGenerate,
    _NearObjectGenerate,
    _NearTextGenerate,
    _NearVectorGenerate,
    _NearVideoGenerate,
):
    pass


class _GroupByCollection(
    _NearAudioGroupBy,
    _NearImageGroupBy,
    _NearObjectGroupBy,
    _NearTextGroupBy,
    _NearVectorGroupBy,
    _NearVideoGroupBy,
):
    pass


class _GrpcCollectionModel(Generic[Model], _Grpc[Any]):
    def __init__(
        self,
        connection: Connection,
        name: str,
        model: Type[Model],
        tenant: Optional[str] = None,
        consistency_level: Optional[ConsistencyLevel] = None,
    ):
        super().__init__(connection, name, consistency_level, tenant, type_=model)
        self.model = model

    def __parse_result(
        self,
        properties: "search_get_pb2.PropertiesResult",
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
                        metadata=self._extract_metadata_for_object(prop.metadata)._to_return(),
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
        metadata = self._extract_metadata_for_object(res.metadata)._to_return()
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
