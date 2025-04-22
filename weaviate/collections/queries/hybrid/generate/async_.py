from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.hybrid.generate.executor import _HybridGenerateExecutor
from weaviate.connect.v4 import ConnectionAsync


@executor.wrap("async")
class _HybridGenerateAsync(
    Generic[Properties, References],
    _HybridGenerateExecutor[ConnectionAsync, Properties, References],
):
    pass
