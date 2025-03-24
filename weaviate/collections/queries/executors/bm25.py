from typing import Any, Generic, List, Optional, Union, cast

from weaviate.collections.classes.filters import _Filters
from weaviate.collections.classes.grpc import GroupBy, Rerank, METADATA
from weaviate.collections.classes.internal import (
    QueryReturnType,
    GenerativeReturnType,
    ReturnProperties,
    ReturnReferences,
    _QueryOptions,
    _Generative,
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
from weaviate.types import INCLUDE_VECTOR


class _BM25GenerateExecutor(Generic[Properties, References], _BaseExecutor):
    def bm25(
        self,
        *,
        connection: Connection,
        query: Optional[str],
        single_prompt: Union[str, _SinglePrompt, None] = None,
        grouped_task: Union[str, _GroupedTask, None] = None,
        grouped_properties: Optional[List[str]],
        generative_provider: Optional[_GenerativeConfigRuntime],
        query_properties: Optional[List[str]],
        limit: Optional[int],
        offset: Optional[int],
        auto_limit: Optional[int],
        filters: Optional[_Filters],
        group_by: Optional[GroupBy],
        rerank: Optional[Rerank],
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA],
        return_properties: Optional[ReturnProperties[TProperties]],
        return_references: Optional[ReturnReferences[TReferences]],
    ) -> ExecutorResult[GenerativeReturnType[Properties, References, TProperties, TReferences]]:
        if group_by is not None and not connection.supports_groupby_in_bm25_and_hybrid():
            raise WeaviateUnsupportedFeatureError(
                "BM25 group by", connection.server_version, "1.25.0"
            )

        def resp(
            res: SearchReply,
        ) -> GenerativeReturnType[Properties, References, TProperties, TReferences]:
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

        request = self._query.bm25(
            query=query,
            properties=query_properties,
            limit=limit,
            offset=offset,
            autocut=auto_limit,
            filters=filters,
            group_by=_GroupBy.from_input(group_by),
            rerank=rerank,
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
        return execute(response_callback=resp, method=connection.grpc_search, request=request)


class _BM25QueryExecutor(Generic[Properties, References], _BaseExecutor):
    def bm25(
        self,
        *,
        connection: Connection,
        query: Optional[str],
        query_properties: Optional[List[str]],
        limit: Optional[int],
        offset: Optional[int],
        auto_limit: Optional[int],
        filters: Optional[_Filters],
        group_by: Optional[GroupBy],
        rerank: Optional[Rerank],
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA],
        return_properties: Optional[ReturnProperties[TProperties]],
        return_references: Optional[ReturnReferences[TReferences]],
    ) -> ExecutorResult[QueryReturnType[Properties, References, TProperties, TReferences]]:
        if group_by is not None and not connection.supports_groupby_in_bm25_and_hybrid():
            raise WeaviateUnsupportedFeatureError(
                "BM25 group by", connection.server_version, "1.25.0"
            )

        def resp(
            res: SearchReply,
        ) -> QueryReturnType[Properties, References, TProperties, TReferences]:
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

        request = self._query.bm25(
            query=query,
            properties=query_properties,
            limit=limit,
            offset=offset,
            autocut=auto_limit,
            filters=filters,
            group_by=_GroupBy.from_input(group_by),
            rerank=rerank,
            return_metadata=self._parse_return_metadata(return_metadata, include_vector),
            return_properties=self._parse_return_properties(return_properties),
            return_references=self._parse_return_references(cast(Any, return_references)),
        )
        return execute(
            response_callback=resp,
            method=connection.grpc_search,
            request=request,
        )
