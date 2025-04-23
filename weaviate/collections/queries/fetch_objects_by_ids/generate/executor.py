from typing import Any, Generic, List, Literal, Iterable, Optional, Type, Union, cast, overload

from weaviate.collections.classes.filters import Filter
from weaviate.collections.classes.grpc import METADATA, Sorting, PROPERTIES, REFERENCES
from weaviate.collections.classes.internal import (
    GenerativeReturnType,
    GenerativeReturn,
    CrossReferences,
    ReturnProperties,
    ReturnReferences,
    _QueryOptions,
    _Generative,
    _GenerativeConfigRuntime,
    _SinglePrompt,
    _GroupedTask,
)
from weaviate.collections.classes.types import Properties, TProperties, References, TReferences
from weaviate.collections.queries.base_executor import _BaseExecutor
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync, ConnectionType

from weaviate.proto.v1.search_get_pb2 import SearchReply
from weaviate.types import UUID, INCLUDE_VECTOR


class _FetchObjectsByIDsGenerateExecutor(
    Generic[ConnectionType, Properties, References], _BaseExecutor[ConnectionType]
):
    @overload
    def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        single_prompt: Union[str, _SinglePrompt, None] = None,
        grouped_task: Union[str, _GroupedTask, None] = None,
        grouped_properties: Optional[List[str]] = None,
        generative_provider: Optional[_GenerativeConfigRuntime] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: Literal[None] = None
    ) -> executor.Result[GenerativeReturn[Properties, References]]: ...

    @overload
    def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        single_prompt: Union[str, _SinglePrompt, None] = None,
        grouped_task: Union[str, _GroupedTask, None] = None,
        grouped_properties: Optional[List[str]] = None,
        generative_provider: Optional[_GenerativeConfigRuntime] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: REFERENCES
    ) -> executor.Result[GenerativeReturn[Properties, CrossReferences]]: ...

    @overload
    def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        single_prompt: Union[str, _SinglePrompt, None] = None,
        grouped_task: Union[str, _GroupedTask, None] = None,
        grouped_properties: Optional[List[str]] = None,
        generative_provider: Optional[_GenerativeConfigRuntime] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Union[PROPERTIES, bool, None] = None,
        return_references: Type[TReferences]
    ) -> executor.Result[GenerativeReturn[Properties, TReferences]]: ...

    @overload
    def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        single_prompt: Union[str, _SinglePrompt, None] = None,
        grouped_task: Union[str, _GroupedTask, None] = None,
        grouped_properties: Optional[List[str]] = None,
        generative_provider: Optional[_GenerativeConfigRuntime] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Type[TProperties],
        return_references: Literal[None] = None
    ) -> executor.Result[GenerativeReturn[TProperties, References]]: ...

    @overload
    def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        single_prompt: Union[str, _SinglePrompt, None] = None,
        grouped_task: Union[str, _GroupedTask, None] = None,
        grouped_properties: Optional[List[str]] = None,
        generative_provider: Optional[_GenerativeConfigRuntime] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Type[TProperties],
        return_references: REFERENCES
    ) -> executor.Result[GenerativeReturn[TProperties, CrossReferences]]: ...

    @overload
    def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        single_prompt: Union[str, _SinglePrompt, None] = None,
        grouped_task: Union[str, _GroupedTask, None] = None,
        grouped_properties: Optional[List[str]] = None,
        generative_provider: Optional[_GenerativeConfigRuntime] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Type[TProperties],
        return_references: Type[TReferences]
    ) -> executor.Result[GenerativeReturn[TProperties, TReferences]]: ...

    @overload
    def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        single_prompt: Union[str, _SinglePrompt, None] = None,
        grouped_task: Union[str, _GroupedTask, None] = None,
        grouped_properties: Optional[List[str]] = None,
        generative_provider: Optional[_GenerativeConfigRuntime] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None
    ) -> executor.Result[
        GenerativeReturnType[Properties, References, TProperties, TReferences]
    ]: ...

    def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        single_prompt: Union[str, _SinglePrompt, None] = None,
        grouped_task: Union[str, _GroupedTask, None] = None,
        grouped_properties: Optional[List[str]] = None,
        generative_provider: Optional[_GenerativeConfigRuntime] = None,
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
