from typing import Generic

from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.bm25.generate.executor import _BM25GenerateExecutor
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync


@executor.wrap("sync")
class _BM25Generate(
    Generic[Properties, References],
    _BM25GenerateExecutor[ConnectionSync, Properties, References],
):
    pass
