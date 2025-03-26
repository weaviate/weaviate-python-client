from typing import (
    Generic,
    Literal,
    Optional,
    Type,
    Union,
    overload,
)

from weaviate.collections.classes.grpc import PROPERTIES, REFERENCES
from weaviate.collections.classes.internal import (
    ObjectSingleReturn,
    CrossReferences,
    ReturnProperties,
    ReturnReferences,
    QuerySingleReturn,
)
from weaviate.collections.classes.types import Properties, TProperties, References, TReferences
from weaviate.collections.queries.fetch_object_by_id.base import _FetchObjectByIDQueryBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync
from weaviate.types import INCLUDE_VECTOR, UUID

class _FetchObjectByIDQueryAsync(
    Generic[Properties, References],
    _FetchObjectByIDQueryBase[ConnectionAsync, Properties, References],
):
    @overload
    async def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: Literal[None] = None,
    ) -> ObjectSingleReturn[Properties, References]: ...
    @overload
    async def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: REFERENCES,
    ) -> ObjectSingleReturn[Properties, CrossReferences]: ...
    @overload
    async def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Union[PROPERTIES, bool, None] = None,
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
    @overload
    async def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None,
    ) -> QuerySingleReturn[Properties, References, TProperties, TReferences]: ...

class _FetchObjectByIDQuery(
    Generic[Properties, References],
    _FetchObjectByIDQueryBase[ConnectionSync, Properties, References],
):
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: Literal[None] = None,
    ) -> ObjectSingleReturn[Properties, References]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: REFERENCES,
    ) -> ObjectSingleReturn[Properties, CrossReferences]: ...
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Union[PROPERTIES, bool, None] = None,
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
    @overload
    def fetch_object_by_id(
        self,
        uuid: UUID,
        include_vector: INCLUDE_VECTOR = False,
        *,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None,
    ) -> QuerySingleReturn[Properties, References, TProperties, TReferences]: ...
