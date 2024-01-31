from typing import Generic, List, Literal, Optional, Type, Union, overload
from weaviate.collections.classes.filters import (
    _Filters,
)
from weaviate.collections.classes.grpc import Rerank, METADATA, PROPERTIES, REFERENCES
from weaviate.collections.classes.internal import (
    QueryReturn,
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

class _BM25Query(Generic[Properties, References], _BaseQuery[Properties, References]):
    @overload
    def bm25(
        self,
        query: str,
        *,
        query_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[False] = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None
    ) -> QueryReturn[Properties, None, None]: ...
    @overload
    def bm25(
        self,
        query: str,
        *,
        query_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[False] = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: REFERENCES
    ) -> QueryReturn[Properties, CrossReferences, None]: ...
    @overload
    def bm25(
        self,
        query: str,
        *,
        query_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[False] = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Type[TReferences]
    ) -> QueryReturn[Properties, TReferences, None]: ...
    @overload
    def bm25(
        self,
        query: str,
        *,
        query_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[False] = False,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None
    ) -> QueryReturn[TProperties, None, None]: ...
    @overload
    def bm25(
        self,
        query: str,
        *,
        query_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[False] = False,
        return_properties: Type[TProperties],
        return_references: REFERENCES
    ) -> QueryReturn[TProperties, CrossReferences, None]: ...
    @overload
    def bm25(
        self,
        query: str,
        *,
        query_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[False] = False,
        return_properties: Type[TProperties],
        return_references: Type[TReferences]
    ) -> QueryReturn[TProperties, TReferences, None]: ...
    @overload
    def bm25(
        self,
        query: str,
        *,
        query_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[True],
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None
    ) -> QueryReturn[Properties, None, Vectors]: ...
    @overload
    def bm25(
        self,
        query: str,
        *,
        query_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[True],
        return_properties: Optional[PROPERTIES] = None,
        return_references: REFERENCES
    ) -> QueryReturn[Properties, CrossReferences, Vectors]: ...
    @overload
    def bm25(
        self,
        query: str,
        *,
        query_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[True],
        return_properties: Optional[PROPERTIES] = None,
        return_references: Type[TReferences]
    ) -> QueryReturn[Properties, TReferences, Vectors]: ...
    @overload
    def bm25(
        self,
        query: str,
        *,
        query_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[True],
        return_properties: Type[TProperties],
        return_references: Literal[None] = None
    ) -> QueryReturn[TProperties, None, Vectors]: ...
    @overload
    def bm25(
        self,
        query: str,
        *,
        query_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[True],
        return_properties: Type[TProperties],
        return_references: REFERENCES
    ) -> QueryReturn[TProperties, CrossReferences, Vectors]: ...
    @overload
    def bm25(
        self,
        query: str,
        *,
        query_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: Literal[True],
        return_properties: Type[TProperties],
        return_references: Type[TReferences]
    ) -> QueryReturn[TProperties, TReferences, Vectors]: ...
    @overload
    def bm25(
        self,
        query: str,
        *,
        query_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: bool = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None
    ) -> Union[QueryReturn[Properties, None, None], QueryReturn[Properties, None, Vectors]]: ...
    @overload
    def bm25(
        self,
        query: str,
        *,
        query_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: bool = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: REFERENCES
    ) -> Union[
        QueryReturn[Properties, CrossReferences, None],
        QueryReturn[Properties, CrossReferences, Vectors],
    ]: ...
    @overload
    def bm25(
        self,
        query: str,
        *,
        query_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: bool = False,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Type[TReferences]
    ) -> Union[
        QueryReturn[Properties, TReferences, None], QueryReturn[Properties, TReferences, Vectors]
    ]: ...
    @overload
    def bm25(
        self,
        query: str,
        *,
        query_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: bool = False,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None
    ) -> Union[QueryReturn[TProperties, None, None], QueryReturn[TProperties, None, Vectors]]: ...
    @overload
    def bm25(
        self,
        query: str,
        *,
        query_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: bool = False,
        return_properties: Type[TProperties],
        return_references: REFERENCES
    ) -> Union[
        QueryReturn[TProperties, CrossReferences, None],
        QueryReturn[TProperties, CrossReferences, Vectors],
    ]: ...
    @overload
    def bm25(
        self,
        query: str,
        *,
        query_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        return_metadata: Optional[METADATA] = None,
        include_vector: bool = False,
        return_properties: Type[TProperties],
        return_references: Type[TReferences]
    ) -> Union[
        QueryReturn[TProperties, TReferences, None], QueryReturn[TProperties, TReferences, Vectors]
    ]: ...
