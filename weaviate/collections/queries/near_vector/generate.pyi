from typing import Generic, List, Literal, Optional, Type, overload

from weaviate.collections.classes.filters import (
    _Filters,
)
from weaviate.collections.classes.grpc import METADATA, PROPERTIES, REFERENCES, Rerank
from weaviate.collections.classes.internal import (
    _GenerativeReturn,
    References,
    CrossReferences,
    TReferences,
)
from weaviate.collections.classes.types import (
    Properties,
    TProperties,
)
from weaviate.collections.queries.base import _BaseQuery

class _NearVectorGenerate(Generic[Properties, References], _BaseQuery[Properties, References]):
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Literal[None] = None,
    ) -> _GenerativeReturn[Properties, References]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: REFERENCES,
    ) -> _GenerativeReturn[Properties, CrossReferences]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Optional[PROPERTIES] = None,
        return_references: Type[TReferences],
    ) -> _GenerativeReturn[Properties, TReferences]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None,
    ) -> _GenerativeReturn[TProperties, References]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Type[TProperties],
        return_references: REFERENCES,
    ) -> _GenerativeReturn[TProperties, CrossReferences]: ...
    @overload
    def near_vector(
        self,
        near_vector: List[float],
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        certainty: Optional[float] = None,
        distance: Optional[float] = None,
        limit: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        rerank: Optional[Rerank] = None,
        include_vector: bool = False,
        return_metadata: Optional[METADATA] = None,
        *,
        return_properties: Type[TProperties],
        return_references: Type[TReferences],
    ) -> _GenerativeReturn[TProperties, TReferences]: ...
