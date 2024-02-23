from typing import (
    Generic,
    Literal,
    Optional,
    Type,
    overload,
)

from weaviate.collections.classes.grpc import PROPERTIES, REFERENCES
from weaviate.collections.classes.internal import (
    ObjectSingleReturn,
    CrossReferences,
)
from weaviate.collections.classes.types import Properties, TProperties, References, TReferences
from weaviate.collections.queries.base import _BaseQuery
from weaviate.types import INCLUDE_VECTOR, UUID

class _FetchObjectByIDQuery(Generic[Properties, References], _BaseQuery[Properties, References]):
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None,
    ) -> ObjectSingleReturn[Properties, References]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: REFERENCES,
    ) -> ObjectSingleReturn[Properties, CrossReferences]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Type[TReferences],
    ) -> ObjectSingleReturn[Properties, TReferences]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None,
    ) -> ObjectSingleReturn[TProperties, References]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Type[TProperties],
        return_references: REFERENCES,
    ) -> ObjectSingleReturn[TProperties, CrossReferences]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Type[TProperties],
        return_references: Type[TReferences],
    ) -> ObjectSingleReturn[TProperties, TReferences]: ...
