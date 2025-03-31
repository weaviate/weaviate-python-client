from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.hybrid.executors import _HybridQueryExecutor
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@executor.wrap("async")
class _HybridQueryAsync(
    Generic[Properties, References], _HybridQueryExecutor[ConnectionAsync, Properties, References]
):
    pass


@executor.wrap("sync")
class _HybridQuery(
    Generic[Properties, References], _HybridQueryExecutor[ConnectionSync, Properties, References]
):
    pass
