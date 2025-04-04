from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.fetch_objects.executors import _FetchObjectsQueryExecutor
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@executor.wrap("async")
class _FetchObjectsQueryAsync(
    Generic[Properties, References],
    _FetchObjectsQueryExecutor[ConnectionAsync, Properties, References],
):
    pass


@executor.wrap("sync")
class _FetchObjectsQuery(
    Generic[Properties, References],
    _FetchObjectsQueryExecutor[ConnectionSync, Properties, References],
):
    pass
