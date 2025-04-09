from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_vector.executors import _NearVectorQueryExecutor
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@executor.wrap("async")
class _NearVectorQueryAsync(
    Generic[Properties, References],
    _NearVectorQueryExecutor[ConnectionAsync, Properties, References],
):
    pass


@executor.wrap("sync")
class _NearVectorQuery(
    Generic[Properties, References],
    _NearVectorQueryExecutor[ConnectionSync, Properties, References],
):
    pass
