from typing import Any, Generic, List, Literal, Optional, Type, Union, cast, overload
from weaviate.collections.classes.filters import _Filters
from weaviate.collections.classes.grpc import (
    METADATA,
    PROPERTIES,
    REFERENCES,
    GroupBy,
    HybridFusion,
    Rerank,
    HybridVectorType,
    TargetVectorJoinType,
)
from weaviate.collections.classes.internal import (
    QuerySearchReturnType,
    QueryReturn,
    GroupByReturn,
    CrossReferences,
    ReturnProperties,
    ReturnReferences,
    _QueryOptions,
    _GroupBy,
)
from weaviate.collections.classes.types import Properties, TProperties, References, TReferences
from weaviate.collections.queries.base_executor import _BaseExecutor
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionType
from weaviate.exceptions import WeaviateUnsupportedFeatureError
from weaviate.proto.v1.search_get_pb2 import SearchReply
from weaviate.types import NUMBER, INCLUDE_VECTOR
from weaviate.connect.v4 import ConnectionSync
from .executor import _HybridQueryExecutor

class _HybridQuery(
    Generic[Properties, References], _HybridQueryExecutor[ConnectionSync, Properties, References]
):
    @overload
    def hybrid(
        self,
        query: Optional[str],
        *,
        alpha: NUMBER = 0.7,
        vector: Optional[HybridVectorType] = None,
        query_properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        max_vector_distance: Optional[NUMBER] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Literal[None] = None,
        rerank: Optional[Rerank] = None,
        target_vector: Optional[TargetVectorJoinType] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: Literal[None] = None
    ) -> QueryReturn[Properties, References]: ...
    @overload
    def hybrid(
        self,
        query: Optional[str],
        *,
        alpha: NUMBER = 0.7,
        vector: Optional[HybridVectorType] = None,
        query_properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        max_vector_distance: Optional[NUMBER] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Literal[None] = None,
        rerank: Optional[Rerank] = None,
        target_vector: Optional[TargetVectorJoinType] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: REFERENCES
    ) -> QueryReturn[Properties, CrossReferences]: ...
    @overload
    def hybrid(
        self,
        query: Optional[str],
        *,
        alpha: NUMBER = 0.7,
        vector: Optional[HybridVectorType] = None,
        query_properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        max_vector_distance: Optional[NUMBER] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Literal[None] = None,
        rerank: Optional[Rerank] = None,
        target_vector: Optional[TargetVectorJoinType] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: Type[TReferences]
    ) -> QueryReturn[Properties, TReferences]: ...
    @overload
    def hybrid(
        self,
        query: Optional[str],
        *,
        alpha: NUMBER = 0.7,
        vector: Optional[HybridVectorType] = None,
        query_properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        max_vector_distance: Optional[NUMBER] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Literal[None] = None,
        rerank: Optional[Rerank] = None,
        target_vector: Optional[TargetVectorJoinType] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None
    ) -> QueryReturn[TProperties, References]: ...
    @overload
    def hybrid(
        self,
        query: Optional[str],
        *,
        alpha: NUMBER = 0.7,
        vector: Optional[HybridVectorType] = None,
        query_properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        max_vector_distance: Optional[NUMBER] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Literal[None] = None,
        rerank: Optional[Rerank] = None,
        target_vector: Optional[TargetVectorJoinType] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Type[TProperties],
        return_references: REFERENCES
    ) -> QueryReturn[TProperties, CrossReferences]: ...
    @overload
    def hybrid(
        self,
        query: Optional[str],
        *,
        alpha: NUMBER = 0.7,
        vector: Optional[HybridVectorType] = None,
        query_properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        max_vector_distance: Optional[NUMBER] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Literal[None] = None,
        rerank: Optional[Rerank] = None,
        target_vector: Optional[TargetVectorJoinType] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Type[TProperties],
        return_references: Type[TReferences]
    ) -> QueryReturn[TProperties, TReferences]: ...
    @overload
    def hybrid(
        self,
        query: Optional[str],
        *,
        alpha: NUMBER = 0.7,
        vector: Optional[HybridVectorType] = None,
        query_properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        max_vector_distance: Optional[NUMBER] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: GroupBy,
        rerank: Optional[Rerank] = None,
        target_vector: Optional[TargetVectorJoinType] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: Literal[None] = None
    ) -> GroupByReturn[Properties, References]: ...
    @overload
    def hybrid(
        self,
        query: Optional[str],
        *,
        alpha: NUMBER = 0.7,
        vector: Optional[HybridVectorType] = None,
        query_properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        max_vector_distance: Optional[NUMBER] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: GroupBy,
        rerank: Optional[Rerank] = None,
        target_vector: Optional[TargetVectorJoinType] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: REFERENCES
    ) -> GroupByReturn[Properties, CrossReferences]: ...
    @overload
    def hybrid(
        self,
        query: Optional[str],
        *,
        alpha: NUMBER = 0.7,
        vector: Optional[HybridVectorType] = None,
        query_properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        max_vector_distance: Optional[NUMBER] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: GroupBy,
        rerank: Optional[Rerank] = None,
        target_vector: Optional[TargetVectorJoinType] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: Type[TReferences]
    ) -> GroupByReturn[Properties, TReferences]: ...
    @overload
    def hybrid(
        self,
        query: Optional[str],
        *,
        alpha: NUMBER = 0.7,
        vector: Optional[HybridVectorType] = None,
        query_properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        max_vector_distance: Optional[NUMBER] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: GroupBy,
        rerank: Optional[Rerank] = None,
        target_vector: Optional[TargetVectorJoinType] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None
    ) -> GroupByReturn[TProperties, References]: ...
    @overload
    def hybrid(
        self,
        query: Optional[str],
        *,
        alpha: NUMBER = 0.7,
        vector: Optional[HybridVectorType] = None,
        query_properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        max_vector_distance: Optional[NUMBER] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: GroupBy,
        rerank: Optional[Rerank] = None,
        target_vector: Optional[TargetVectorJoinType] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Type[TProperties],
        return_references: REFERENCES
    ) -> GroupByReturn[TProperties, CrossReferences]: ...
    @overload
    def hybrid(
        self,
        query: Optional[str],
        *,
        alpha: NUMBER = 0.7,
        vector: Optional[HybridVectorType] = None,
        query_properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        max_vector_distance: Optional[NUMBER] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: GroupBy,
        rerank: Optional[Rerank] = None,
        target_vector: Optional[TargetVectorJoinType] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Type[TProperties],
        return_references: Type[TReferences]
    ) -> GroupByReturn[TProperties, TReferences]: ...
    @overload
    def hybrid(
        self,
        query: Optional[str],
        *,
        alpha: NUMBER = 0.7,
        vector: Optional[HybridVectorType] = None,
        query_properties: Optional[List[str]] = None,
        fusion_type: Optional[HybridFusion] = None,
        max_vector_distance: Optional[NUMBER] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Optional[GroupBy] = None,
        rerank: Optional[Rerank] = None,
        target_vector: Optional[TargetVectorJoinType] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None
    ) -> QuerySearchReturnType[Properties, References, TProperties, TReferences]: ...
