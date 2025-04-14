from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.fetch_objects_by_ids.executors import (
    _FetchObjectsByIdsQueryExecutor,
)
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@executor.wrap("async")
class _FetchObjectsByIDsQueryAsync(
    Generic[Properties, References],
    _FetchObjectsByIdsQueryExecutor[ConnectionAsync, Properties, References],
):
    pass


@executor.wrap("sync")
class _FetchObjectsByIDsQuery(
    Generic[Properties, References],
    _FetchObjectsByIdsQueryExecutor[ConnectionSync, Properties, References],
):
    pass
