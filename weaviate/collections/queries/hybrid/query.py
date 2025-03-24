from typing import Generic, List, Optional

from weaviate import syncify
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
    QuerySearchReturnType,
    ReturnProperties,
    ReturnReferences,
)
from weaviate.collections.classes.types import Properties, TProperties, References, TReferences
from weaviate.collections.queries.base import _BaseQuery
from weaviate.connect.executor import aresult
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync
from weaviate.types import NUMBER, INCLUDE_VECTOR


class _HybridQueryAsync(
    Generic[Properties, References], _BaseQuery[ConnectionAsync, Properties, References]
):
    async def hybrid(
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
    ) -> QuerySearchReturnType[Properties, References, TProperties, TReferences]:
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
        return await aresult(
            self._executor.hybrid(
                connection=self._connection,
                query=query,
                alpha=alpha,
                vector=vector,
                query_properties=query_properties,
                fusion_type=fusion_type,
                max_vector_distance=max_vector_distance,
                limit=limit,
                offset=offset,
                auto_limit=auto_limit,
                filters=filters,
                group_by=group_by,
                rerank=rerank,
                target_vector=target_vector,
                include_vector=include_vector,
                return_metadata=return_metadata,
                return_properties=return_properties,
                return_references=return_references,
            )
        )


@syncify.convert(_HybridQueryAsync)
class _HybridQuery(
    Generic[Properties, References], _BaseQuery[ConnectionSync, Properties, References]
):
    pass
