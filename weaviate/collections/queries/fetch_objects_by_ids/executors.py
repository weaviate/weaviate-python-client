from typing import Any, Generic, List, Iterable, Optional, Union, cast

from weaviate.collections.classes.filters import Filter
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
from weaviate.collections.queries.executor import _BaseExecutor
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync, ConnectionType

from weaviate.proto.v1.search_get_pb2 import SearchReply
from weaviate.types import UUID, INCLUDE_VECTOR


class _FetchObjectsByIdsGenerateExecutor(
    Generic[ConnectionType, Properties, References], _BaseExecutor[ConnectionType]
):
    def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        single_prompt: Union[str, _SinglePrompt, None] = None,
        grouped_task: Union[str, _GroupedTask, None] = None,
        grouped_properties: Optional[List[str]] = None,
        generative_provider: Optional[_GenerativeConfigRuntime],
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None
    ) -> executor.Result[GenerativeReturnType[Properties, References, TProperties, TReferences]]:
        """Perform retrieval-augmented generation (RAG) on the results of a simple get query of objects matching the provided IDs in this collection.

        See the docstring of `fetch_objects` for more information on the arguments.
        """

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

        if not ids:
            if isinstance(self._connection, ConnectionAsync):

                async def _execute() -> (
                    GenerativeReturnType[Properties, References, TProperties, TReferences]
                ):
                    return resp(SearchReply())

                return _execute()
            return resp(SearchReply())

        request = self._query.get(
            limit=limit,
            offset=offset,
            after=after,
            filters=Filter.any_of([Filter.by_id().equal(uuid) for uuid in ids]),
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
        return executor.execute(
            response_callback=resp,
            method=self._connection.grpc_search,
            request=request,
        )


class _FetchObjectsByIdsQueryExecutor(
    Generic[ConnectionType, Properties, References], _BaseExecutor[ConnectionType]
):
    def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None
    ) -> executor.Result[QueryReturnType[Properties, References, TProperties, TReferences]]:
        """Perform a special case of fetch_objects based on filters on uuid.

        See the docstring of `fetch_objects` for more information on the arguments.
        """

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

        if not ids:
            if isinstance(self._connection, ConnectionAsync):

                async def _execute() -> (
                    QueryReturnType[Properties, References, TProperties, TReferences]
                ):
                    return resp(SearchReply())

                return _execute()
            return resp(SearchReply())

        request = self._query.get(
            limit=limit,
            offset=offset,
            after=after,
            filters=Filter.any_of([Filter.by_id().equal(uuid) for uuid in ids]),
            sort=sort,
            return_metadata=self._parse_return_metadata(return_metadata, include_vector),
            return_properties=self._parse_return_properties(return_properties),
            return_references=self._parse_return_references(cast(Any, return_references)),
        )
        return executor.execute(
            response_callback=resp,
            method=self._connection.grpc_search,
            request=request,
        )
