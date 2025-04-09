from typing import (
    Generic,
)

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.fetch_object_by_id.executor import _FetchObjectsByIdQueryExecutor
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@executor.wrap("async")
class _FetchObjectByIDQueryAsync(
    Generic[Properties, References],
    _FetchObjectsByIdQueryExecutor[ConnectionAsync, Properties, References],
):
    pass


@executor.wrap("sync")
class _FetchObjectByIDQuery(
    Generic[Properties, References],
    _FetchObjectsByIdQueryExecutor[ConnectionSync, Properties, References],
):
    pass
