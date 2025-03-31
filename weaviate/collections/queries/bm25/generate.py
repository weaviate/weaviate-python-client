from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.bm25.executors import _BM25GenerateExecutor
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@executor.wrap("async")
class _BM25GenerateAsync(
    Generic[Properties, References], _BM25GenerateExecutor[ConnectionAsync, Properties, References]
):
    pass


@executor.wrap("sync")
class _BM25Generate(
    Generic[Properties, References], _BM25GenerateExecutor[ConnectionSync, Properties, References]
):
    pass
