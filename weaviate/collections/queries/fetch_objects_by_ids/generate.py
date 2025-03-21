from typing import Generic, Iterable, List, Optional, Union

from weaviate import syncify
from weaviate.collections.classes.filters import Filter
from weaviate.collections.classes.generative import (
    _GenerativeConfigRuntime,
    _GroupedTask,
    _SinglePrompt,
)
from weaviate.collections.classes.grpc import METADATA, Sorting
from weaviate.collections.classes.internal import (
    GenerativeReturnType,
    _Generative,
    ReturnProperties,
    ReturnReferences,
    _QueryOptions,
)
from weaviate.collections.classes.types import Properties, TProperties, References, TReferences
from weaviate.collections.queries.base import _Base
from weaviate.proto.v1 import search_get_pb2
from weaviate.types import UUID, INCLUDE_VECTOR


class _FetchObjectsByIDsGenerateAsync(
    Generic[Properties, References], _Base[Properties, References]
):
    async def fetch_objects_by_ids(
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
    ) -> GenerativeReturnType[Properties, References, TProperties, TReferences]:
        """Perform retrieval-augmented generation (RAG) on the results of a simple get query of objects matching the provided IDs in this collection.

        See the docstring of `fetch_objects` for more information on the arguments.
        """
        if not ids:
            res = search_get_pb2.SearchReply(results=None)
        else:
            res = await self._query.get(
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
        return self._result_to_generative_query_return(
            res,
            _QueryOptions.from_input(
                return_metadata,
                return_properties,
                include_vector,
                self._references,
                return_references,
            ),
            return_properties,
            return_references,
        )


@syncify.convert
class _FetchObjectsByIDsGenerate(
    Generic[Properties, References], _FetchObjectsByIDsGenerateAsync[Properties, References]
):
    pass
