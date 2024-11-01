from typing import Generic, Iterable, Literal, Optional, Type, Union, overload

from weaviate.collections.classes.grpc import METADATA, PROPERTIES, REFERENCES, Sorting
from weaviate.collections.classes.internal import (
    QueryReturn,
    CrossReferences,
    ReturnProperties,
    ReturnReferences,
    QueryReturnType,
)
from weaviate.collections.classes.types import Properties, TProperties, References, TReferences
from weaviate.collections.queries.base import _Base
from weaviate.types import UUID, INCLUDE_VECTOR

class _FetchObjectsByIDsQueryAsync(Generic[Properties, References], _Base[Properties, References]):
    @overload
    async def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: Literal[None] = None
    ) -> QueryReturn[Properties, References]: ...
    @overload
    async def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: REFERENCES
    ) -> QueryReturn[Properties, CrossReferences]: ...
    @overload
    async def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: Type[TReferences]
    ) -> QueryReturn[Properties, TReferences]: ...
    @overload
    async def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None
    ) -> QueryReturn[TProperties, References]: ...
    @overload
    async def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Type[TProperties],
        return_references: REFERENCES
    ) -> QueryReturn[TProperties, CrossReferences]: ...
    @overload
    async def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Type[TProperties],
        return_references: Type[TReferences]
    ) -> QueryReturn[TProperties, TReferences]: ...
    @overload
    async def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None
    ) -> QueryReturnType[Properties, References, TProperties, TReferences]: ...

class _FetchObjectsByIDsQuery(Generic[Properties, References], _Base[Properties, References]):
    @overload
    def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: Literal[None] = None
    ) -> QueryReturn[Properties, References]: ...
    @overload
    def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: REFERENCES
    ) -> QueryReturn[Properties, CrossReferences]: ...
    @overload
    def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: Type[TReferences]
    ) -> QueryReturn[Properties, TReferences]: ...
    @overload
    def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None
    ) -> QueryReturn[TProperties, References]: ...
    @overload
    def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Type[TProperties],
        return_references: REFERENCES
    ) -> QueryReturn[TProperties, CrossReferences]: ...
    @overload
    def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Type[TProperties],
        return_references: Type[TReferences]
    ) -> QueryReturn[TProperties, TReferences]: ...
    @overload
    def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None
    ) -> QueryReturnType[Properties, References, TProperties, TReferences]: ...
