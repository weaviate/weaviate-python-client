from typing import Any, Generic, List, Optional, Union, cast

from weaviate.collections.classes.filters import _Filters
from weaviate.collections.classes.grpc import GroupBy, Rerank, METADATA
from weaviate.collections.classes.internal import (
    QuerySearchReturnType,
    GenerativeSearchReturnType,
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
from weaviate.collections.queries.executor import _BaseExecutor
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionType
from weaviate.exceptions import WeaviateUnsupportedFeatureError
from weaviate.proto.v1.search_get_pb2 import SearchReply
from weaviate.types import INCLUDE_VECTOR


class _BM25GenerateExecutor(
    Generic[ConnectionType, Properties, References], _BaseExecutor[ConnectionType]
):
    def bm25(
        self,
        query: Optional[str],
        *,
        single_prompt: Union[str, _SinglePrompt, None] = None,
        grouped_task: Union[str, _GroupedTask, None] = None,
        grouped_properties: Optional[List[str]] = None,
        generative_provider: Optional[_GenerativeConfigRuntime] = None,
        query_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Optional[GroupBy] = None,
        rerank: Optional[Rerank] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None,
    ) -> executor.Result[
        GenerativeSearchReturnType[Properties, References, TProperties, TReferences]
    ]:
        """Perform retrieval-augmented generation (RAG) on the results of a keyword-based BM25 search of objects in this collection.

        See the [docs](https://weaviate.io/developers/weaviate/search/bm25) for a more detailed explanation.

        Arguments:
            `query`
                The keyword-based query to search for, REQUIRED. If None, a normal search will be performed.
            `single_prompt`
                The prompt to use for generative query on each object individually.
            `grouped_task`
                The prompt to use for generative query on the entire result set.
            `grouped_properties`
                The properties to use in the generative query on the entire result set.
            `generative_provider`
                Specify the generative provider and provier-specific options with a suitable `GenerativeProvider.<provider>()` factory function.
            `query_properties`
                The properties to search in. If not specified, all properties are searched.
            `limit`
                The maximum number of results to return. If not specified, the default limit specified by the server is returned.
            `offset`
                The offset to start from. If not specified, the retrieval begins from the first object in the server.
            `auto_limit`
                The maximum number of [autocut](https://weaviate.io/developers/weaviate/api/graphql/additional-operators#autocut) results to return. If not specified, no limit is applied.
            `filters`
                The filters to apply to the search.
            `group_by`
                How the results should be grouped by a specific property.
            `rerank`
                How the results should be reranked. NOTE: A `rerank-*` module must be enabled for this functionality to work.
            `include_vector`
                Whether to include the vector in the results. If not specified, this is set to False.
            `return_metadata`
                The metadata to return for each object, defaults to `None`.
            `return_properties`
                The properties to return for each object.
            `return_references`
                The references to return for each object.

        NOTE:
            If `return_properties` is not provided then all non-reference properties are returned including nested properties.
            If `return_metadata` is not provided then no metadata is provided. Use MetadataQuery.full() to retrieve all metadata.
            If `return_references` is not provided then no references are provided.

        Returns:
            A `GenerativeReturn` or `GenerativeGroupByReturn` object that includes the searched objects.
            If `group_by` is provided then a `GenerativeGroupByReturn` object is returned, otherwise a `GenerativeReturn` object is returned.

        Raises:
            `weaviate.exceptions.WeaviateQueryError`:
                If the network connection to Weaviate fails.
            `weaviate.exceptions.WeaviateUnsupportedFeatureError`:
                If a group by is provided and the Weaviate server version is lower than 1.25.0.
        """
        if group_by is not None and not self._connection.supports_groupby_in_bm25_and_hybrid():
            raise WeaviateUnsupportedFeatureError(
                "BM25 group by", self._connection.server_version, "1.25.0"
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
        return executor.execute(
            response_callback=resp, method=self._connection.grpc_search, request=request
        )


class _BM25QueryExecutor(
    Generic[ConnectionType, Properties, References], _BaseExecutor[ConnectionType]
):
    def bm25(
        self,
        query: Optional[str],
        *,
        query_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        auto_limit: Optional[int] = None,
        filters: Optional[_Filters] = None,
        group_by: Optional[GroupBy] = None,
        rerank: Optional[Rerank] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None,
    ) -> executor.Result[QuerySearchReturnType[Properties, References, TProperties, TReferences]]:
        """Search for objects in this collection using the keyword-based BM25 algorithm.

        See the [docs](https://weaviate.io/developers/weaviate/search/bm25) for a more detailed explanation.

        Arguments:
            `query`
                The keyword-based query to search for, REQUIRED. If None, a normal search will be performed.
            `query_properties`
                The properties to search in. If not specified, all properties are searched.
            `limit`
                The maximum number of results to return. If not specified, the default limit specified by the server is returned.
            `offset`
                The offset to start from. If not specified, the retrieval begins from the first object in the server.
            `auto_limit`
                The maximum number of [autocut](https://weaviate.io/developers/weaviate/api/graphql/additional-operators#autocut) results to return. If not specified, no limit is applied.
            `filters`
                The filters to apply to the search.
            `group_by`
                How the results should be grouped by a specific property.
            `rerank`
                How the results should be reranked. NOTE: A `rerank-*` module must be enabled for this functionality to work.
            `include_vector`
                Whether to include the vector in the results. If not specified, this is set to False.
            `return_metadata`
                The metadata to return for each object, defaults to `None`.
            `return_properties`
                The properties to return for each object.

        NOTE:
            If `return_properties` is not provided then all non-reference properties are returned including nested properties.
            If `return_metadata` is not provided then no metadata is provided. Use MetadataQuery.full() to retrieve all metadata.
            If `return_references` is not provided then no references are provided.

        Returns:
            A `QueryReturn` or `GroupByReturn` object that includes the searched objects.
            If `group_by` is provided then a `GroupByReturn` object is returned, otherwise a `QueryReturn` object is returned.

        Raises:
            `weaviate.exceptions.WeaviateQueryError`:
                If the network connection to Weaviate fails.
            `weaviate.exceptions.WeaviateNotImplementedError`:
                If a group by is provided and the Weaviate server version is lower than 1.25.0.
        """
        if group_by is not None and not self._connection.supports_groupby_in_bm25_and_hybrid():
            raise WeaviateUnsupportedFeatureError(
                "BM25 group by", self._connection.server_version, "1.25.0"
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
        return executor.execute(
            response_callback=resp,
            method=self._connection.grpc_search,
            request=request,
        )
