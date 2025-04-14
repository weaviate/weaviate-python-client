from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_text.executors import _NearTextQueryExecutor
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@executor.wrap("async")
class _NearTextQueryAsync(
    Generic[Properties, References], _NearTextQueryExecutor[ConnectionAsync, Properties, References]
):
    pass


@executor.wrap("sync")
class _NearTextQuery(
    Generic[Properties, References], _NearTextQueryExecutor[ConnectionSync, Properties, References]
):
    pass
