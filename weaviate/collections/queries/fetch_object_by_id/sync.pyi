from typing import Generic, Literal, Optional, Type, Union, cast, overload
from weaviate.collections.classes.filters import Filter
from weaviate.collections.classes.grpc import PROPERTIES, REFERENCES, MetadataQuery
from weaviate.collections.classes.internal import (
    CrossReferences,
    MetadataSingleObjectReturn,
    ObjectSingleReturn,
    QuerySingleReturn,
    ReturnProperties,
    ReturnReferences,
    _QueryOptions,
)
from weaviate.collections.classes.types import Properties, References, TProperties, TReferences
from weaviate.collections.queries.base_executor import _BaseExecutor
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionType
from weaviate.proto.v1.search_get_pb2 import SearchReply
from weaviate.types import INCLUDE_VECTOR, UUID
from weaviate.connect.v4 import ConnectionSync
from .executor import _FetchObjectByIDQueryExecutor

class _FetchObjectByIDQuery(
    Generic[Properties, References],
    _FetchObjectByIDQueryExecutor[ConnectionSync, Properties, References],
):
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: Literal[None] = None
    ) -> ObjectSingleReturn[Properties, References]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: REFERENCES
    ) -> ObjectSingleReturn[Properties, CrossReferences]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: Type[TReferences]
    ) -> ObjectSingleReturn[Properties, TReferences]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None
    ) -> ObjectSingleReturn[TProperties, References]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Type[TProperties],
        return_references: REFERENCES
    ) -> ObjectSingleReturn[TProperties, CrossReferences]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Type[TProperties],
        return_references: Type[TReferences]
    ) -> ObjectSingleReturn[TProperties, TReferences]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None
    ) -> QuerySingleReturn[Properties, References, TProperties, TReferences]: ...
