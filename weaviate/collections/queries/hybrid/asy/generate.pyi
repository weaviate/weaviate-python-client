from typing import Generic, List, Literal, Optional, Type, overload

from weaviate.collections.classes.filters import (
    _Filters,
)
from weaviate.collections.classes.grpc import METADATA, PROPERTIES, REFERENCES, HybridFusion, Rerank
from weaviate.collections.classes.internal import (
    GenerativeReturn,
    CrossReferences,
)
from weaviate.collections.classes.types import Properties, TProperties, References, TReferences
from weaviate.collections.queries.base_async import _BaseAsync
from weaviate.types import NUMBER, INCLUDE_VECTOR

class _HybridGenerateAsync(Generic[Properties, References], _BaseAsync[Properties, References]):
    @overload
    async def hybrid(
        self,
        query: Optional[str],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        alpha: NUMBER = 0.5,
        vector: Optional[List[float]] = None,
        query_properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        target_vector: Optional[str] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None,
    ) -> GenerativeReturn[Properties, References]: ...
    @overload
    async def hybrid(
        self,
        query: Optional[str],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        alpha: NUMBER = 0.5,
        vector: Optional[List[float]] = None,
        query_properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        target_vector: Optional[str] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Optional[PROPERTIES] = None,
        return_references: REFERENCES,
    ) -> GenerativeReturn[Properties, CrossReferences]: ...
    @overload
    async def hybrid(
        self,
        query: Optional[str],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        alpha: NUMBER = 0.5,
        vector: Optional[List[float]] = None,
        query_properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        target_vector: Optional[str] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Type[TReferences],
    ) -> GenerativeReturn[Properties, TReferences]: ...
    @overload
    async def hybrid(
        self,
        query: Optional[str],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        alpha: NUMBER = 0.5,
        vector: Optional[List[float]] = None,
        query_properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        target_vector: Optional[str] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None,
    ) -> GenerativeReturn[TProperties, References]: ...
    @overload
    async def hybrid(
        self,
        query: Optional[str],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        alpha: NUMBER = 0.5,
        vector: Optional[List[float]] = None,
        query_properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        target_vector: Optional[str] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Type[TProperties],
        return_references: REFERENCES,
    ) -> GenerativeReturn[TProperties, CrossReferences]: ...
    @overload
    async def hybrid(
        self,
        query: Optional[str],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        alpha: NUMBER = 0.5,
        vector: Optional[List[float]] = None,
        query_properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        target_vector: Optional[str] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Type[TProperties],
        return_references: Type[TReferences],
    ) -> GenerativeReturn[TProperties, TReferences]: ...
