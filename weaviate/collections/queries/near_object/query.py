from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_object.executors import _NearObjectQueryExecutor
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@executor.wrap("async")
class _NearObjectQueryAsync(
    Generic[Properties, References],
    _NearObjectQueryExecutor[ConnectionAsync, Properties, References],
):
    pass


@executor.wrap("sync")
class _NearObjectQuery(
    Generic[Properties, References],
    _NearObjectQueryExecutor[ConnectionSync, Properties, References],
):
    pass
