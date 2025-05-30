from typing import Generic, Literal, Optional, Type, Union, overload

from weaviate.collections.classes.filters import _Filters
from weaviate.collections.classes.grpc import METADATA, PROPERTIES, REFERENCES, Sorting
from weaviate.collections.classes.internal import (
    CrossReferences,
    QueryReturn,
    QueryReturnType,
    ReturnProperties,
    ReturnReferences,
)
from weaviate.collections.classes.types import Properties, References, TProperties, TReferences
from weaviate.connect.v4 import ConnectionAsync
from weaviate.types import INCLUDE_VECTOR, UUID

from .executor import _FetchObjectsQueryExecutor

class _FetchObjectsQueryAsync(
    Generic[Properties, References],
    _FetchObjectsQueryExecutor[ConnectionAsync, Properties, References],
):
    @overload
    async def fetch_objects(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: Literal[None] = None,
    ) -> QueryReturn[Properties, References]: ...
    @overload
    async def fetch_objects(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: REFERENCES,
    ) -> QueryReturn[Properties, CrossReferences]: ...
    @overload
    async def fetch_objects(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: Type[TReferences],
    ) -> QueryReturn[Properties, TReferences]: ...
    @overload
    async def fetch_objects(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None,
    ) -> QueryReturn[TProperties, References]: ...
    @overload
    async def fetch_objects(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Type[TProperties],
        return_references: REFERENCES,
    ) -> QueryReturn[TProperties, CrossReferences]: ...
    @overload
    async def fetch_objects(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Type[TProperties],
        return_references: Type[TReferences],
    ) -> QueryReturn[TProperties, TReferences]: ...
    @overload
    async def fetch_objects(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None,
    ) -> QueryReturnType[Properties, References, TProperties, TReferences]: ...
