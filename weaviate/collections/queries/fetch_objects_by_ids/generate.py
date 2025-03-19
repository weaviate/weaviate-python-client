from typing import Generic, Iterable, List, Optional

from weaviate import syncify
from weaviate.collections.classes.filters import Filter
from weaviate.collections.classes.grpc import METADATA, Sorting
from weaviate.collections.classes.internal import (
    GenerativeReturnType,
    _Generative,
    ReturnProperties,
    ReturnReferences,
    _QueryOptions,
)
from weaviate.collections.classes.types import Properties, TProperties, References, TReferences
from weaviate.collections.queries.base import _BaseGenerate
from weaviate.connect.v4 import ConnectionAsync
from weaviate.proto.v1 import search_get_pb2
from weaviate.types import UUID, INCLUDE_VECTOR


class _FetchObjectsByIDsGenerateAsync(
    Generic[Properties, References], _BaseGenerate[ConnectionAsync, Properties, References]
):
    async def fetch_objects_by_ids(
        self,
        ids: Iterable[UUID],
        *,
        single_prompt: Optional[str] = None,
        grouped_task: Optional[str] = None,
        grouped_properties: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        after: Optional[UUID] = None,
        sort: Optional[Sorting] = None,
        include_vector: INCLUDE_VECTOR = False,
        return_metadata: Optional[METADATA] = None,
        return_properties: Optional[ReturnProperties[TProperties]] = None,
        return_references: Optional[ReturnReferences[TReferences]] = None
    ) -> GenerativeReturnType[Properties, References, TProperties, TReferences]:
        """Special case of fetch_objects based on filters on uuid"""
        return await self._executor.fetch_objects(
            self._connection,
            single_prompt=single_prompt,
            grouped_task=grouped_task,
            grouped_properties=grouped_properties,
            limit=limit,
            offset=offset,
            after=after,
            filters=Filter.any_of([Filter.by_id().equal(uuid) for uuid in ids]),
            sort=sort,
            include_vector=include_vector,
            return_metadata=return_metadata,
            return_properties=return_properties,
            return_references=return_references,
        )


@syncify.convert
class _FetchObjectsByIDsGenerate(
    Generic[Properties, References], _FetchObjectsByIDsGenerateAsync[Properties, References]
):
    pass
