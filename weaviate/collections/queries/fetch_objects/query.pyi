from typing import Generic, List, Literal, Optional, Union, Type, overload

from weaviate.collections.classes.filters import (
    _Filters,
)
from weaviate.collections.classes.grpc import (
    METADATA,
    PROPERTIES,
    REFERENCES,
    Sort,
)
from weaviate.collections.classes.internal import (
    QueryReturn,
    References,
    TReferences,
    CrossReferences,
)
from weaviate.collections.classes.types import Properties, TProperties
from weaviate.collections.queries.base import _BaseQuery
from weaviate.types import UUID

class _FetchObjectsQuery(Generic[Properties, References], _BaseQuery[Properties, References]):
    @overload
    def fetch_objects(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[Union[Sort, List[Sort]]] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None
    ) -> QueryReturn[Properties, References]: ...
    @overload
    def fetch_objects(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[Union[Sort, List[Sort]]] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Optional[PROPERTIES] = None,
        return_references: REFERENCES
    ) -> QueryReturn[Properties, CrossReferences]: ...
    @overload
    def fetch_objects(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[Union[Sort, List[Sort]]] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Type[TReferences]
    ) -> QueryReturn[Properties, TReferences]: ...
    @overload
    def fetch_objects(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[Union[Sort, List[Sort]]] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None
    ) -> QueryReturn[TProperties, References]: ...
    @overload
    def fetch_objects(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[Union[Sort, List[Sort]]] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Type[TProperties],
        return_references: REFERENCES
    ) -> QueryReturn[TProperties, CrossReferences]: ...
    @overload
    def fetch_objects(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[Union[Sort, List[Sort]]] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Type[TProperties],
        return_references: Type[TReferences]
    ) -> QueryReturn[TProperties, TReferences]: ...
