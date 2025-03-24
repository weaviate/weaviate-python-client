from typing import Generic, Iterable, Optional

from weaviate import syncify
from weaviate.collections.classes.grpc import METADATA, Sorting
from weaviate.collections.classes.internal import (
    QueryReturnType,
    ReturnProperties,
    ReturnReferences,
)
from weaviate.collections.classes.types import Properties, TProperties, References, TReferences
from weaviate.collections.queries.base import _BaseQuery
from weaviate.connect.executor import aresult
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync
from weaviate.types import UUID, INCLUDE_VECTOR


class _FetchObjectsByIDsQueryAsync(
    Generic[Properties, References], _BaseQuery[ConnectionAsync, Properties, References]
):
    async def fetch_objects_by_ids(
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
    ) -> QueryReturnType[Properties, References, TProperties, TReferences]:
        """Perform a special case of fetch_objects based on filters on uuid."""
        return await aresult(
            self._executor.fetch_objects_by_ids(
                connection=self._connection,
                ids=ids,
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


@syncify.convert(_FetchObjectsByIDsQueryAsync)
class _FetchObjectsByIDsQuery(
    Generic[Properties, References], _BaseQuery[ConnectionSync, Properties, References]
):
    pass
