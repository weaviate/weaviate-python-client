from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.hybrid.executors import _HybridGenerateExecutor
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@executor.wrap("async")
class _HybridGenerateAsync(
    Generic[Properties, References],
    _HybridGenerateExecutor[ConnectionAsync, Properties, References],
):
    pass


@executor.wrap("sync")
class _HybridGenerate(
    Generic[Properties, References], _HybridGenerateExecutor[ConnectionSync, Properties, References]
):
    pass
