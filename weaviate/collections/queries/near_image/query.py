from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_image.executors import _NearImageQueryExecutor
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@executor.wrap("async")
class _NearImageQueryAsync(
    Generic[Properties, References],
    _NearImageQueryExecutor[ConnectionAsync, Properties, References],
):
    pass


@executor.wrap("sync")
class _NearImageQuery(
    Generic[Properties, References], _NearImageQueryExecutor[ConnectionSync, Properties, References]
):
    pass
