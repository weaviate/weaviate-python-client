from typing import Generic

from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.hybrid.query.executor import _HybridQueryExecutor
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync


@executor.wrap("async")
class _HybridQueryAsync(
    Generic[Properties, References],
    _HybridQueryExecutor[ConnectionAsync, Properties, References],
):
    pass
