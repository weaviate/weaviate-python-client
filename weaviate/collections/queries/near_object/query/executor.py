from typing import Any, Generic, Literal, Optional, Type, Union, cast, overload

from weaviate.collections.classes.filters import (
    _Filters,
)
from weaviate.collections.classes.grpc import (
    METADATA,
    PROPERTIES,
    REFERENCES,
    GroupBy,
    Rerank,
    TargetVectorJoinType,
)
from weaviate.collections.classes.internal import (
    CrossReferences,
    GroupByReturn,
    QueryNearMediaReturnType,
    QueryReturn,
    QuerySearchReturnType,
    ReturnProperties,
    ReturnReferences,
    _GroupBy,
    _QueryOptions,
)
from weaviate.collections.classes.types import (
    Properties,
    References,
    TProperties,
    TReferences,
)
from weaviate.collections.queries.base_executor import _BaseExecutor
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionType
from weaviate.proto.v1 import search_get_pb2
from weaviate.types import INCLUDE_VECTOR, NUMBER, UUID


class _NearObjectQueryExecutor(
    Generic[ConnectionType, Properties, References], _BaseExecutor[ConnectionType]
):
    @overload
    def near_object(
        self,
        near_object: UUID,
        *,
        certainty: Optional[NUMBER] = None,
        distance: Optional[NUMBER] = None,
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
        return_references: Literal[None] = None,
    ) -> executor.Result[QueryReturn[Properties, References]]: ...

    @overload
    def near_object(
        self,
        near_object: UUID,
        *,
        certainty: Optional[NUMBER] = None,
        distance: Optional[NUMBER] = None,
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
        return_references: REFERENCES,
    ) -> executor.Result[QueryReturn[Properties, CrossReferences]]: ...

    @overload
    def near_object(
        self,
        near_object: UUID,
        *,
        certainty: Optional[NUMBER] = None,
        distance: Optional[NUMBER] = None,
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
        return_references: Type[TReferences],
    ) -> executor.Result[QueryReturn[Properties, TReferences]]: ...

    @overload
    def near_object(
        self,
        near_object: UUID,
        *,
        certainty: Optional[NUMBER] = None,
        distance: Optional[NUMBER] = None,
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
        return_references: Literal[None] = None,
    ) -> executor.Result[QueryReturn[TProperties, References]]: ...

    @overload
    def near_object(
        self,
        near_object: UUID,
        *,
        certainty: Optional[NUMBER] = None,
        distance: Optional[NUMBER] = None,
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
        return_references: REFERENCES,
    ) -> executor.Result[QueryReturn[TProperties, CrossReferences]]: ...

    @overload
    def near_object(
        self,
        near_object: UUID,
        *,
        certainty: Optional[NUMBER] = None,
        distance: Optional[NUMBER] = None,
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
        return_references: Type[TReferences],
    ) -> executor.Result[QueryReturn[TProperties, TReferences]]: ...

    ### GroupBy ###

    @overload
    def near_object(
        self,
        near_object: UUID,
        *,
        certainty: Optional[NUMBER] = None,
        distance: Optional[NUMBER] = None,
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
        return_references: Literal[None] = None,
    ) -> executor.Result[GroupByReturn[Properties, References]]: ...

    @overload
    def near_object(
        self,
        near_object: UUID,
        *,
        certainty: Optional[NUMBER] = None,
        distance: Optional[NUMBER] = None,
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
        return_references: REFERENCES,
    ) -> executor.Result[GroupByReturn[Properties, CrossReferences]]: ...

    @overload
    def near_object(
        self,
        near_object: UUID,
        *,
        certainty: Optional[NUMBER] = None,
        distance: Optional[NUMBER] = None,
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
        return_references: Type[TReferences],
    ) -> executor.Result[GroupByReturn[Properties, TReferences]]: ...

    @overload
    def near_object(
        self,
        near_object: UUID,
        *,
        certainty: Optional[NUMBER] = None,
        distance: Optional[NUMBER] = None,
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
        return_references: Literal[None] = None,
    ) -> executor.Result[GroupByReturn[TProperties, References]]: ...

    @overload
    def near_object(
        self,
        near_object: UUID,
        *,
        certainty: Optional[NUMBER] = None,
        distance: Optional[NUMBER] = None,
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
        return_references: REFERENCES,
    ) -> executor.Result[GroupByReturn[TProperties, CrossReferences]]: ...

    @overload
    def near_object(
        self,
        near_object: UUID,
        *,
        certainty: Optional[NUMBER] = None,
        distance: Optional[NUMBER] = None,
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
        return_references: Type[TReferences],
    ) -> executor.Result[GroupByReturn[TProperties, TReferences]]: ...

    ### Default ###

    @overload
    def near_object(
        self,
        near_object: UUID,
        *,
        certainty: Optional[NUMBER] = None,
        distance: Optional[NUMBER] = None,
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
        QuerySearchReturnType[Properties, References, TProperties, TReferences]
    ]: ...

    def near_object(
        self,
        near_object: UUID,
        *,
        certainty: Optional[NUMBER] = None,
        distance: Optional[NUMBER] = None,
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
        QueryNearMediaReturnType[Properties, References, TProperties, TReferences]
    ]:
        """Search for objects in this collection by another object using a vector-based similarity search.

        See the [docs](https://weaviate.io/developers/weaviate/api/graphql/search-operators#nearobject) for a more detailed explanation.

        Args:
            near_object: The UUID of the object to search on, REQUIRED.
            certainty: The minimum similarity score to return. If not specified, the default certainty specified by the server is used.
            distance: The maximum distance to search. If not specified, the default distance specified by the server is used.
            limit: The maximum number of results to return. If not specified, the default limit specified by the server is returned.
            offset: The offset to start from. If not specified, the retrieval begins from the first object in the server.
            auto_limit: The maximum number of [autocut](https://weaviate.io/developers/weaviate/api/graphql/additional-operators#autocut) results to return. If not specified, no limit is applied.
            filters: The filters to apply to the search.
            group_by: How the results should be grouped by a specific property.
            rerank: How the results should be reranked. NOTE: A `rerank-*` module must be enabled for this functionality to work.
            target_vector: The name of the vector space to search in for named vector configurations. Required if multiple spaces are configured.
            include_vector: Whether to include the vector in the results. If not specified, this is set to False.
            return_metadata: The metadata to return for each object, defaults to `None`.
            return_properties: The properties to return for each object.
            return_references: The references to return for each object.

        NOTE:
            - If `return_properties` is not provided then all properties are returned except for blob properties.
            - If `return_metadata` is not provided then no metadata is provided. Use MetadataQuery.full() to retrieve all metadata.
            - If `return_references` is not provided then no references are provided.

        Returns:
            A `QueryReturn` or `GroupByReturn` object that includes the searched objects.
            If `group_by` is provided then a `GroupByReturn` object is returned, otherwise a `QueryReturn` object is returned.

        Raises:
            weaviate.exceptions.WeaviateGRPCQueryError: If the request to the Weaviate server fails.
        """

        def resp(
            res: search_get_pb2.SearchReply,
        ) -> QueryNearMediaReturnType[Properties, References, TProperties, TReferences]:
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

        request = self._query.near_object(
            near_object=near_object,
            certainty=certainty,
            distance=distance,
            limit=limit,
            offset=offset,
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
            response_callback=resp, method=self._connection.grpc_search, request=request
        )
