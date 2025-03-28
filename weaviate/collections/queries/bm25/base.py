from typing import Generic

from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.bm25.executors import _BM25GenerateExecutor, _BM25QueryExecutor
from weaviate.connect.v4 import ConnectionType


class _BM25GenerateBase(
    Generic[ConnectionType, Properties, References],
    _BM25GenerateExecutor[Properties, References],
):
    pass


class _BM25QueryBase(
    Generic[ConnectionType, Properties, References],
    _BM25QueryExecutor[Properties, References],
):
    pass
