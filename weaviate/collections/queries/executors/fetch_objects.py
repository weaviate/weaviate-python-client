from typing import Any, Generic, List, Optional, Union, cast

from weaviate.collections.classes.filters import _Filters
from weaviate.collections.classes.grpc import METADATA, Sorting
from weaviate.collections.classes.internal import (
    QueryReturnType,
    GenerativeReturnType,
    ReturnProperties,
    ReturnReferences,
    _QueryOptions,
    _Generative,
    _GenerativeConfigRuntime,
    _SinglePrompt,
    _GroupedTask,
)
from weaviate.collections.classes.types import Properties, TProperties, References, TReferences
from weaviate.collections.queries.executors.base import _BaseExecutor
from weaviate.connect.v4 import Connection
from weaviate.connect.executor import ExecutorResult, execute
from weaviate.proto.v1.search_get_pb2 import SearchReply
from weaviate.types import UUID, INCLUDE_VECTOR


class _FetchObjectsGenerateExecutor(Generic[Properties, References], _BaseExecutor):
    def fetch_objects(
        self,
        *,
        connection: Connection,
        single_prompt: Union[str, _SinglePrompt, None] = None,
        grouped_task: Union[str, _GroupedTask, None] = None,
        grouped_properties: Optional[List[str]],
        generative_provider: Optional[_GenerativeConfigRuntime],
        limit: Optional[int],
        offset: Optional[int],
        after: Optional[UUID],
        filters: Optional[_Filters],
        sort: Optional[Sorting],
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA],
        return_properties: Optional[ReturnProperties[TProperties]],
        return_references: Optional[ReturnReferences[TReferences]]
    ) -> ExecutorResult[GenerativeReturnType[Properties, References, TProperties, TReferences]]:
        def resp(
            res: SearchReply,
        ) -> GenerativeReturnType[Properties, References, TProperties, TReferences]:
            return cast(
                Any,
                self._result_to_generative_query_return(
                    res,
                    _QueryOptions.from_input(
                        return_metadata,
                        return_properties,
                        include_vector,
                        self._references,
                        return_references,
                    ),
                ),
            )

        request = self._query.get(
            limit=limit,
            offset=offset,
            after=after,
            filters=filters,
            sort=sort,
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


class _FetchObjectsQueryExecutor(Generic[Properties, References], _BaseExecutor):
    def fetch_objects(
        self,
        *,
        connection: Connection,
        limit: Optional[int],
        offset: Optional[int],
        after: Optional[UUID],
        filters: Optional[_Filters],
        sort: Optional[Sorting],
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA],
        return_properties: Optional[ReturnProperties[TProperties]],
        return_references: Optional[ReturnReferences[TReferences]]
    ) -> ExecutorResult[QueryReturnType[Properties, References, TProperties, TReferences]]:
        def resp(
            res: SearchReply,
        ) -> QueryReturnType[Properties, References, TProperties, TReferences]:
            return cast(
                Any,
                self._result_to_query_return(
                    res,
                    _QueryOptions.from_input(
                        return_metadata,
                        return_properties,
                        include_vector,
                        self._references,
                        return_references,
                    ),
                ),
            )

        request = self._query.get(
            limit=limit,
            offset=offset,
            after=after,
            filters=filters,
            sort=sort,
            return_metadata=self._parse_return_metadata(return_metadata, include_vector),
            return_properties=self._parse_return_properties(return_properties),
            return_references=self._parse_return_references(cast(Any, return_references)),
        )
        return execute(
            response_callback=resp,
            method=connection.grpc_search,
            request=request,
        )
