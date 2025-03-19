from typing import Any, Awaitable, Generic, List, Optional, Union, cast, overload

from weaviate import syncify
from weaviate.collections.classes.filters import _Filters
from weaviate.collections.classes.grpc import METADATA, Sorting
from weaviate.collections.classes.internal import (
    QueryReturnType,
    GenerativeReturnType,
    ReturnProperties,
    ReturnReferences,
    _QueryOptions,
    _Generative,
)
from weaviate.collections.classes.types import Properties, TProperties, References, TReferences
from weaviate.collections.queries.executor import _BaseExecutor
from weaviate.connect.v4 import Connection, ConnectionAsync, ConnectionSync
from weaviate.connect.executor import ExecutorResult, execute, raise_exception
from weaviate.proto.v1.search_get_pb2 import SearchReply
from weaviate.types import UUID, INCLUDE_VECTOR


class _FetchObjectsGenerateExecutor(Generic[Properties, References], _BaseExecutor):
    def fetch_objects(
        self,
        connection: ConnectionAsync,
        *,
        single_prompt: Optional[str],
        grouped_task: Optional[str],
        grouped_properties: Optional[List[str]],
        limit: Optional[int],
        offset: Optional[int],
        after: Optional[UUID],
        filters: Optional[_Filters],
        sort: Optional[Sorting],
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA],
        return_properties: Optional[ReturnProperties[TProperties]],
        return_references: Optional[ReturnReferences[TReferences]]
    ) -> Awaitable[GenerativeReturnType[Properties, References, TProperties, TReferences]]:
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
        connection: ConnectionAsync,
        *,
        limit: Optional[int],
        offset: Optional[int],
        after: Optional[UUID],
        filters: Optional[_Filters],
        sort: Optional[Sorting],
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA],
        return_properties: Optional[ReturnProperties[TProperties]],
        return_references: Optional[ReturnReferences[TReferences]]
    ) -> Awaitable[QueryReturnType[Properties, References, TProperties, TReferences]]:
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
