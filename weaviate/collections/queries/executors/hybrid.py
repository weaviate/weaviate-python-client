from typing import Any, Generic, List, Optional, Union, cast

from weaviate.collections.classes.filters import (
    _Filters,
)
from weaviate.collections.classes.grpc import (
    METADATA,
    GroupBy,
    HybridFusion,
    Rerank,
    HybridVectorType,
    TargetVectorJoinType,
)
from weaviate.collections.classes.internal import (
    GenerativeSearchReturnType,
    QuerySearchReturnType,
    _Generative,
    ReturnProperties,
    ReturnReferences,
    _QueryOptions,
    _GroupBy,
    _GenerativeConfigRuntime,
    _SinglePrompt,
    _GroupedTask,
)
from weaviate.collections.classes.types import Properties, TProperties, References, TReferences
from weaviate.collections.queries.executors.base import _BaseExecutor
from weaviate.connect.v4 import Connection
from weaviate.connect.executor import execute, ExecutorResult
from weaviate.exceptions import WeaviateUnsupportedFeatureError
from weaviate.proto.v1.search_get_pb2 import SearchReply
from weaviate.types import NUMBER, INCLUDE_VECTOR


class _HybridGenerateExecutor(Generic[Properties, References], _BaseExecutor):
    def hybrid(
        self,
        *,
        connection: Connection,
        query: Optional[str],
        single_prompt: Union[str, _SinglePrompt, None] = None,
        grouped_task: Union[str, _GroupedTask, None] = None,
        grouped_properties: Optional[List[str]],
        generative_provider: Optional[_GenerativeConfigRuntime],
        alpha: NUMBER = 0.7,
        vector: Optional[HybridVectorType],
        query_properties: Optional[List[str]],
        fusion_type: Optional[HybridFusion],
        max_vector_distance: Optional[NUMBER],
        limit: Optional[int],
        offset: Optional[int],
        auto_limit: Optional[int],
        filters: Optional[_Filters],
        group_by: Optional[GroupBy],
        rerank: Optional[Rerank],
        target_vector: Optional[TargetVectorJoinType],
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA],
        return_properties: Optional[ReturnProperties[TProperties]],
        return_references: Optional[ReturnReferences[TReferences]],
    ) -> ExecutorResult[
        GenerativeSearchReturnType[Properties, References, TProperties, TReferences]
    ]:
        if group_by is not None and not connection.supports_groupby_in_bm25_and_hybrid():
            raise WeaviateUnsupportedFeatureError(
                "Hybrid group by", connection.server_version, "1.25.0"
            )

        def resp(
            res: SearchReply,
        ) -> GenerativeSearchReturnType[Properties, References, TProperties, TReferences]:
            return cast(
                Any,
                self._result_to_generative_return(
                    res,
                    _QueryOptions.from_input(
                        return_metadata,
                        return_properties,
                        include_vector,
                        self._references,
                        return_references,
                        rerank,
                        group_by,
                    ),
                ),
            )

        request = self._query.hybrid(
            query=query,
            alpha=alpha,
            vector=vector,
            properties=query_properties,
            fusion_type=fusion_type,
            limit=limit,
            offset=offset,
            distance=max_vector_distance,
            autocut=auto_limit,
            filters=filters,
            group_by=_GroupBy.from_input(group_by),
            rerank=rerank,
            target_vector=target_vector,
            return_metadata=self._parse_return_metadata(return_metadata, include_vector),
            return_properties=self._parse_return_properties(return_properties),
            return_references=self._parse_return_references(return_references),
            generative=_Generative(
                single=single_prompt,
                grouped=grouped_task,
                grouped_properties=grouped_properties,
                generative_provider=generative_provider,
            ),
        )
        return execute(
            response_callback=resp,
            method=connection.grpc_search,
            request=request,
        )


class _HybridQueryExecutor(Generic[Properties, References], _BaseExecutor):
    def hybrid(
        self,
        *,
        connection: Connection,
        query: Optional[str],
        alpha: NUMBER = 0.7,
        vector: Optional[HybridVectorType],
        query_properties: Optional[List[str]],
        fusion_type: Optional[HybridFusion],
        max_vector_distance: Optional[NUMBER],
        limit: Optional[int],
        offset: Optional[int],
        auto_limit: Optional[int],
        filters: Optional[_Filters],
        group_by: Optional[GroupBy],
        rerank: Optional[Rerank],
        target_vector: Optional[TargetVectorJoinType],
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA],
        return_properties: Optional[ReturnProperties[TProperties]],
        return_references: Optional[ReturnReferences[TReferences]],
    ) -> ExecutorResult[QuerySearchReturnType[Properties, References, TProperties, TReferences]]:
        if group_by is not None and not connection.supports_groupby_in_bm25_and_hybrid():
            raise WeaviateUnsupportedFeatureError(
                "Hybrid group by", connection.server_version, "1.25.0"
            )

        def resp(
            res: SearchReply,
        ) -> QuerySearchReturnType[Properties, References, TProperties, TReferences]:
            return cast(
                Any,
                self._result_to_query_or_groupby_return(
                    res,
                    _QueryOptions.from_input(
                        return_metadata,
                        return_properties,
                        include_vector,
                        self._references,
                        return_references,
                        rerank,
                        group_by,
                    ),
                ),
            )

        request = self._query.hybrid(
            query=query,
            alpha=alpha,
            vector=vector,
            properties=query_properties,
            fusion_type=fusion_type,
            limit=limit,
            offset=offset,
            distance=max_vector_distance,
            autocut=auto_limit,
            filters=filters,
            group_by=_GroupBy.from_input(group_by),
            rerank=rerank,
            target_vector=target_vector,
            return_metadata=self._parse_return_metadata(return_metadata, include_vector),
            return_properties=self._parse_return_properties(return_properties),
            return_references=self._parse_return_references(return_references),
        )
        return execute(
            response_callback=resp,
            method=connection.grpc_search,
            request=request,
        )
