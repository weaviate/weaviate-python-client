from typing import Generic, List, Literal, Optional, Union, Type, overload
from weaviate.collections.classes.filters import _Filters
from weaviate.collections.classes.grpc import (
    METADATA,
    PROPERTIES,
    REFERENCES,
    _Sorting,
)
from weaviate.collections.classes.internal import (
    GenerativeReturn,
    CrossReferences,
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

class _FetchObjectsGenerate(Generic[Properties, References], _BaseQuery[Properties, References]):
    @overload
    def fetch_objects(
        self,
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[False] = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None
    ) -> GenerativeReturn[Properties, None, None]: ...
    @overload
    def fetch_objects(
        self,
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[False] = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: REFERENCES
    ) -> GenerativeReturn[Properties, CrossReferences, None]: ...
    @overload
    def fetch_objects(
        self,
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[False] = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Type[TReferences]
    ) -> GenerativeReturn[Properties, TReferences, None]: ...
    @overload
    def fetch_objects(
        self,
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[False] = False,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None
    ) -> GenerativeReturn[TProperties, None, None]: ...
    @overload
    def fetch_objects(
        self,
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[False] = False,
        return_properties: Type[TProperties],
        return_references: REFERENCES
    ) -> GenerativeReturn[TProperties, CrossReferences, None]: ...
    @overload
    def fetch_objects(
        self,
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[False] = False,
        return_properties: Type[TProperties],
        return_references: Type[TReferences]
    ) -> GenerativeReturn[TProperties, TReferences, None]: ...
    @overload
    def fetch_objects(
        self,
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[True],
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None
    ) -> GenerativeReturn[Properties, None, Vectors]: ...
    @overload
    def fetch_objects(
        self,
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[True],
        return_properties: Optional[PROPERTIES] = None,
        return_references: REFERENCES
    ) -> GenerativeReturn[Properties, CrossReferences, Vectors]: ...
    @overload
    def fetch_objects(
        self,
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[True],
        return_properties: Optional[PROPERTIES] = None,
        return_references: Type[TReferences]
    ) -> GenerativeReturn[Properties, TReferences, Vectors]: ...
    @overload
    def fetch_objects(
        self,
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[True],
        return_properties: Type[TProperties],
        return_references: Literal[None] = None
    ) -> GenerativeReturn[TProperties, None, Vectors]: ...
    @overload
    def fetch_objects(
        self,
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[True],
        return_properties: Type[TProperties],
        return_references: REFERENCES
    ) -> GenerativeReturn[TProperties, CrossReferences, Vectors]: ...
    @overload
    def fetch_objects(
        self,
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[True],
        return_properties: Type[TProperties],
        return_references: Type[TReferences]
    ) -> GenerativeReturn[TProperties, TReferences, Vectors]: ...
    @overload
    def fetch_objects(
        self,
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: bool = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None
    ) -> Union[
        GenerativeReturn[Properties, None, None], GenerativeReturn[Properties, None, Vectors]
    ]: ...
    @overload
    def fetch_objects(
        self,
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
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
        GenerativeReturn[Properties, CrossReferences, None],
        GenerativeReturn[Properties, CrossReferences, Vectors],
    ]: ...
    @overload
    def fetch_objects(
        self,
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
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
        GenerativeReturn[Properties, TReferences, None],
        GenerativeReturn[Properties, TReferences, Vectors],
    ]: ...
    @overload
    def fetch_objects(
        self,
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        filters: Optional[_Filters] = None,
        sort: Optional[_Sorting] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: bool = False,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None
    ) -> Union[
        GenerativeReturn[TProperties, None, None], GenerativeReturn[TProperties, None, Vectors]
    ]: ...
    @overload
    def fetch_objects(
        self,
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
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
        GenerativeReturn[TProperties, CrossReferences, None],
        GenerativeReturn[TProperties, CrossReferences, Vectors],
    ]: ...
    @overload
    def fetch_objects(
        self,
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
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
        GenerativeReturn[TProperties, TReferences, None],
        GenerativeReturn[TProperties, TReferences, Vectors],
    ]: ...
