from io import BufferedReader
from pathlib import Path
from typing import Any, Generic, List, Optional, Union, cast

from weaviate.collections.classes.filters import (
    _Filters,
)
from weaviate.collections.classes.grpc import (
    METADATA,
    GroupBy,
    Rerank,
    NearMediaType,
    TargetVectorJoinType,
)
from weaviate.collections.classes.internal import (
    _Generative,
    _GroupBy,
    GenerativeSearchReturnType,
    QuerySearchReturnType,
    ReturnProperties,
    ReturnReferences,
    _QueryOptions,
)
from weaviate.collections.classes.types import Properties, TProperties, References, TReferences
from weaviate.collections.queries.executors.base import _BaseExecutor
from weaviate.connect.executor import execute, ExecutorResult
from weaviate.connect.v4 import Connection
from weaviate.proto.v1.search_get_pb2 import SearchReply
from weaviate.types import NUMBER, INCLUDE_VECTOR


class _NearImageGenerateExecutor(Generic[Properties, References], _BaseExecutor):
    def near_image(
        self,
        *,
        connection: Connection,
        near_image: Union[str, Path, BufferedReader],
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
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
    ) -> ExecutorResult[
        GenerativeSearchReturnType[Properties, References, TProperties, TReferences]
    ]:
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

        request = self._query.near_media(
            media=self._parse_media(near_image),
            type_=NearMediaType.IMAGE.value,
            certainty=certainty,
            distance=distance,
            filters=filters,
            group_by=_GroupBy.from_input(group_by),
            rerank=rerank,
            target_vector=target_vector,
            generative=_Generative(
                single=single_prompt,
                grouped=grouped_task,
                grouped_properties=grouped_properties,
            ),
            limit=limit,
            offset=offset,
            autocut=auto_limit,
            return_metadata=self._parse_return_metadata(return_metadata, include_vector),
            return_properties=self._parse_return_properties(return_properties),
            return_references=self._parse_return_references(return_references),
        )
        return execute(
            response_callback=resp,
            method=connection.grpc_search,
            request=request,
        )


class _NearImageQueryExecutor(Generic[Properties, References], _BaseExecutor):
    def near_image(
        self,
        *,
        connection: Connection,
        near_image: Union[str, Path, BufferedReader],
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
    ) -> ExecutorResult[QuerySearchReturnType[Properties, References, TProperties, TReferences]]:
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

        request = self._query.near_media(
            media=self._parse_media(near_image),
            type_=NearMediaType.IMAGE.value,
            certainty=certainty,
            distance=distance,
            filters=filters,
            group_by=_GroupBy.from_input(group_by),
            rerank=rerank,
            target_vector=target_vector,
            limit=limit,
            offset=offset,
            autocut=auto_limit,
            return_metadata=self._parse_return_metadata(return_metadata, include_vector),
            return_properties=self._parse_return_properties(return_properties),
            return_references=self._parse_return_references(return_references),
        )
        return execute(
            response_callback=resp,
            method=connection.grpc_search,
            request=request,
        )
