from typing import Generic, Iterable, List, Optional

from weaviate import syncify
from weaviate.collections.classes.grpc import METADATA, Sorting
from weaviate.collections.classes.internal import (
    GenerativeReturnType,
    ReturnProperties,
    ReturnReferences,
)
from weaviate.collections.classes.types import Properties, TProperties, References, TReferences
from weaviate.collections.queries.base import _BaseGenerate
from weaviate.connect.executor import aresult
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync
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
        """Perform a special case of fetch_objects based on filters on uuid."""
        return await aresult(
            self._executor.fetch_objects_by_ids(
                connection=self._connection,
                ids=ids,
                single_prompt=single_prompt,
                grouped_task=grouped_task,
                grouped_properties=grouped_properties,
                limit=limit,
                offset=offset,
                after=after,
                sort=sort,
                include_vector=include_vector,
                return_metadata=return_metadata,
                return_properties=return_properties,
                return_references=return_references,
            )
        )


@syncify.convert_new(_FetchObjectsByIDsGenerateAsync)
class _FetchObjectsByIDsGenerate(
    Generic[Properties, References], _BaseGenerate[ConnectionSync, Properties, References]
):
    pass
