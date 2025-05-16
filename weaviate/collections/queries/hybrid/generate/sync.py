from typing import Generic

from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.hybrid.generate.executor import (
    _HybridGenerateExecutor,
)
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync


@executor.wrap("sync")
class _HybridGenerate(
    Generic[Properties, References],
    _HybridGenerateExecutor[ConnectionSync, Properties, References],
):
    pass
