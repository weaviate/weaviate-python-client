from typing import Generic, List, Literal, Optional, Type, overload

from weaviate.collections.classes.filters import (
    _Filters,
)
from weaviate.collections.classes.grpc import METADATA, PROPERTIES, REFERENCES, HybridFusion, Rerank
from weaviate.collections.classes.internal import (
    _GenerativeQueryReturn,
    References,
    TReferences,
    CrossReferences,
)
from weaviate.collections.classes.types import Properties, TProperties
from weaviate.collections.queries.base import _BaseQuery

class _HybridGenerate(Generic[Properties, References], _BaseQuery[Properties, References]):
    @overload
    def hybrid(
        self,
        query: str,
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        alpha: float = 0.5,
        vector: Optional[List[float]] = None,
        query_properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None,
    ) -> _GenerativeQueryReturn[Properties, References]: ...
    @overload
    def hybrid(
        self,
        query: str,
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        alpha: float = 0.5,
        vector: Optional[List[float]] = None,
        query_properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Optional[PROPERTIES] = None,
        return_references: REFERENCES,
    ) -> _GenerativeQueryReturn[Properties, CrossReferences]: ...
    @overload
    def hybrid(
        self,
        query: str,
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        alpha: float = 0.5,
        vector: Optional[List[float]] = None,
        query_properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Type[TReferences],
    ) -> _GenerativeQueryReturn[Properties, TReferences]: ...
    @overload
    def hybrid(
        self,
        query: str,
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        alpha: float = 0.5,
        vector: Optional[List[float]] = None,
        query_properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None,
    ) -> _GenerativeQueryReturn[TProperties, References]: ...
    @overload
    def hybrid(
        self,
        query: str,
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        alpha: float = 0.5,
        vector: Optional[List[float]] = None,
        query_properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Type[TProperties],
        return_references: REFERENCES,
    ) -> _GenerativeQueryReturn[TProperties, CrossReferences]: ...
    @overload
    def hybrid(
        self,
        query: str,
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        alpha: float = 0.5,
        vector: Optional[List[float]] = None,
        query_properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Type[TProperties],
        return_references: Type[TReferences],
    ) -> _GenerativeQueryReturn[TProperties, TReferences]: ...
