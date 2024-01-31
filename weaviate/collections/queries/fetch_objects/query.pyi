from typing import Generic, Literal, Optional, Union, Type, overload
from weaviate.collections.classes.filters import (
    _Filters,
)
from weaviate.collections.classes.grpc import METADATA, PROPERTIES, REFERENCES, _Sorting
from weaviate.collections.classes.internal import (
    QueryReturn,
    CrossReferences,
    ReturnProperties,
    ReturnReferences,
    QueryReturnType,
)
from weaviate.collections.classes.types import (
    Properties,
    TProperties,
    References,
    TReferences,
    Vectors,
)
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
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[False] = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None
    ) -> QueryReturn[Properties, None, None]: ...
    @overload
    def fetch_objects(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[False] = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: REFERENCES
    ) -> QueryReturn[Properties, CrossReferences, None]: ...
    @overload
    def fetch_objects(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[False] = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Type[TReferences]
    ) -> QueryReturn[Properties, TReferences, None]: ...
    @overload
    def fetch_objects(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[False] = False,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None
    ) -> QueryReturn[TProperties, None, None]: ...
    @overload
    def fetch_objects(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[False] = False,
        return_properties: Type[TProperties],
        return_references: REFERENCES
    ) -> QueryReturn[TProperties, CrossReferences, None]: ...
    @overload
    def fetch_objects(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[False] = False,
        return_properties: Type[TProperties],
        return_references: Type[TReferences]
    ) -> QueryReturn[TProperties, TReferences, None]: ...
    @overload
    def fetch_objects(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[True],
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None
    ) -> QueryReturn[Properties, None, Vectors]: ...
    @overload
    def fetch_objects(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[True],
        return_properties: Optional[PROPERTIES] = None,
        return_references: REFERENCES
    ) -> QueryReturn[Properties, CrossReferences, Vectors]: ...
    @overload
    def fetch_objects(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[True],
        return_properties: Optional[PROPERTIES] = None,
        return_references: Type[TReferences]
    ) -> QueryReturn[Properties, TReferences, Vectors]: ...
    @overload
    def fetch_objects(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[True],
        return_properties: Type[TProperties],
        return_references: Literal[None] = None
    ) -> QueryReturn[TProperties, None, Vectors]: ...
    @overload
    def fetch_objects(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[True],
        return_properties: Type[TProperties],
        return_references: REFERENCES
    ) -> QueryReturn[TProperties, CrossReferences, Vectors]: ...
    @overload
    def fetch_objects(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[True],
        return_properties: Type[TProperties],
        return_references: Type[TReferences]
    ) -> QueryReturn[TProperties, TReferences, Vectors]: ...
    @overload
    def fetch_objects(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: bool = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None
    ) -> Union[QueryReturn[Properties, None, None], QueryReturn[Properties, None, Vectors]]: ...
    @overload
    def fetch_objects(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: bool = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: REFERENCES
    ) -> Union[
        QueryReturn[Properties, CrossReferences, None],
        QueryReturn[Properties, CrossReferences, Vectors],
    ]: ...
    @overload
    def fetch_objects(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: bool = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Type[TReferences]
    ) -> Union[
        QueryReturn[Properties, TReferences, None], QueryReturn[Properties, TReferences, Vectors]
    ]: ...
    @overload
    def fetch_objects(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: bool = False,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None
    ) -> Union[QueryReturn[TProperties, None, None], QueryReturn[TProperties, None, Vectors]]: ...
    @overload
    def fetch_objects(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: bool = False,
        return_properties: Type[TProperties],
        return_references: REFERENCES
    ) -> Union[
        QueryReturn[TProperties, CrossReferences, None],
        QueryReturn[TProperties, CrossReferences, Vectors],
    ]: ...
    @overload
    def fetch_objects(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: bool = False,
        return_properties: Type[TProperties],
        return_references: Type[TReferences]
    ) -> Union[
        QueryReturn[TProperties, TReferences, None], QueryReturn[TProperties, TReferences, Vectors]
    ]: ...
