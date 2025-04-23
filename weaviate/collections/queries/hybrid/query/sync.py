from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.hybrid.query.executor import _HybridQueryExecutor
from weaviate.connect.v4 import ConnectionSync


@executor.wrap("sync")
class _HybridQuery(
    Generic[Properties, References], _HybridQueryExecutor[ConnectionSync, Properties, References]
):
    pass
