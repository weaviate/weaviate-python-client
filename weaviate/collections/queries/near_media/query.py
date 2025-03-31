from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_media.executors import _NearMediaQueryExecutor
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@executor.wrap("async")
class _NearMediaQueryAsync(
    Generic[Properties, References],
    _NearMediaQueryExecutor[ConnectionAsync, Properties, References],
):
    pass


@executor.wrap("sync")
class _NearMediaQuery(
    Generic[Properties, References], _NearMediaQueryExecutor[ConnectionSync, Properties, References]
):
    pass
