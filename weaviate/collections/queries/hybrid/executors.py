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
from weaviate.collections.queries.executor import _BaseExecutor
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionType
from weaviate.exceptions import WeaviateUnsupportedFeatureError
from weaviate.proto.v1.search_get_pb2 import SearchReply
from weaviate.types import NUMBER, INCLUDE_VECTOR


class _HybridGenerateExecutor(
    Generic[ConnectionType, Properties, References], _BaseExecutor[ConnectionType]
):
    def hybrid(
        self,
        query: Optional[str],
        *,
        single_prompt: Union[str, _SinglePrompt, None] = None,
        grouped_task: Union[str, _GroupedTask, None] = None,
        grouped_properties: Optional[List[str]] = None,
        generative_provider: Optional[_GenerativeConfigRuntime] = None,
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
        return_references: Optional[ReturnReferences[TReferences]] = None,
    ) -> executor.Result[
        GenerativeSearchReturnType[Properties, References, TProperties, TReferences]
    ]:
        """Perform retrieval-augmented generation (RAG) on the results of an object search in this collection using the hybrid algorithm blending keyword-based BM25 and vector-based similarity.

        See the [docs](https://weaviate.io/developers/weaviate/search/hybrid) for a more detailed explanation.

        Arguments:
            `query`
                The keyword-based query to search for, REQUIRED. If query and vector are both None, a normal search will be performed.
            `single_prompt`
                The prompt to use for generative query on each object individually.
            `grouped_task`
                The prompt to use for generative query on the entire result set.
            `grouped_properties`
                The properties to use in the generative query on the entire result set.
            `generative_provider`
                Specify the generative provider and provier-specific options with a suitable `GenerativeProvider.<provider>()` factory function.
            `alpha`
                The weight of the BM25 score. If not specified, the default weight specified by the server is used.
            `vector`
                The specific vector to search for. If not specified, the query is vectorized and used in the similarity search.
            `query_properties`
                The properties to search in. If not specified, all properties are searched.
            `fusion_type`
                The type of fusion to apply. If not specified, the default fusion type specified by the server is used.
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
            `target_vector`
                The name of the vector space to search in for named vector configurations. Required if multiple spaces are configured.
            `include_vector`
                Whether to include the vector in the results. If not specified, this is set to False.
            `return_metadata`
                The metadata to return for each object, defaults to `None`.
            `return_properties`
                The properties to return for each object.
            `return_references`
                The references to return for each object.

        NOTE:
            - If `return_properties` is not provided then all properties are returned except for blob properties.
            - If `return_metadata` is not provided then no metadata is provided. Use MetadataQuery.full() to retrieve all metadata.
            - If `return_references` is not provided then no references are provided.

        Returns:
            A `GenerativeReturn` or `GenerativeGroupByReturn` object that includes the searched objects.
            If `group_by` is provided then a `GenerativeGroupByReturn` object is returned, otherwise a `GenerativeReturn` object is returned.

        Raises:
            `weaviate.exceptions.WeaviateQueryError`:
                If the network connection to Weaviate fails.
            `weaviate.exceptions.WeaviateNotImplementedError`:
                If a group by is provided and the Weaviate server version is lower than 1.25.0.
        """
        if group_by is not None and not self._connection.supports_groupby_in_bm25_and_hybrid():
            raise WeaviateUnsupportedFeatureError(
                "Hybrid group by", self._connection.server_version, "1.25.0"
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
        return executor.execute(
            response_callback=resp,
            method=self._connection.grpc_search,
            request=request,
        )


class _HybridQueryExecutor(
    Generic[ConnectionType, Properties, References], _BaseExecutor[ConnectionType]
):
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
        return_references: Optional[ReturnReferences[TReferences]] = None,
    ) -> executor.Result[QuerySearchReturnType[Properties, References, TProperties, TReferences]]:
        """Search for objects in this collection using the hybrid algorithm blending keyword-based BM25 and vector-based similarity.

        See the [docs](https://weaviate.io/developers/weaviate/search/hybrid) for a more detailed explanation.

        Arguments:
            `query`
                The keyword-based query to search for, REQUIRED. If query and vector are both None, a normal search will be performed.
            `alpha`
                The weight of the BM25 score. If not specified, the default weight specified by the server is used.
            `vector`
                The specific vector to search for. If not specified, the query is vectorized and used in the similarity search.
            `query_properties`
                The properties to search in. If not specified, all properties are searched.
            `fusion_type`
                The type of fusion to apply. If not specified, the default fusion type specified by the server is used.
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
            `target_vector`
                The name of the vector space to search in for named vector configurations. Required if multiple spaces are configured.
            `include_vector`
                Whether to include the vector in the results. If not specified, this is set to False.
            `return_metadata`
                The metadata to return for each object, defaults to `None`.
            `return_properties`
                The properties to return for each object.
            `return_references`
                The references to return for each object.

        NOTE:
            - If `return_properties` is not provided then all properties are returned except for blob properties.
            - If `return_metadata` is not provided then no metadata is provided. Use MetadataQuery.full() to retrieve all metadata.
            - If `return_references` is not provided then no references are provided.

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
                "Hybrid group by", self._connection.server_version, "1.25.0"
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
        return executor.execute(
            response_callback=resp,
            method=self._connection.grpc_search,
            request=request,
        )
