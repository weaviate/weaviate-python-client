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
from weaviate.collections.queries.base_async import _BaseAsync
from weaviate.types import INCLUDE_VECTOR, UUID

class _FetchObjectByIDQueryAsync(
    Generic[Properties, References], _BaseAsync[Properties, References]
):
    @overload
    async def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None,
    ) -> ObjectSingleReturn[Properties, References]: ...
    @overload
    async def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: REFERENCES,
    ) -> ObjectSingleReturn[Properties, CrossReferences]: ...
    @overload
    async def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Type[TReferences],
    ) -> ObjectSingleReturn[Properties, TReferences]: ...
    @overload
    async def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None,
    ) -> ObjectSingleReturn[TProperties, References]: ...
    @overload
    async def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Type[TProperties],
        return_references: REFERENCES,
    ) -> Optional[ObjectSingleReturn[TProperties, CrossReferences]]: ...
    @overload
    async def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Type[TProperties],
        return_references: Type[TReferences],
    ) -> ObjectSingleReturn[TProperties, TReferences]: ...
