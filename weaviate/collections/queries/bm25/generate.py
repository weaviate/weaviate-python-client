from typing import Generic

from weaviate.connect import impl
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.bm25.base import _BM25GenerateBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@impl.wrap("async")
class _BM25GenerateAsync(
    Generic[Properties, References], _BM25GenerateBase[ConnectionAsync, Properties, References]
):
    pass


@impl.wrap("sync")
class _BM25Generate(
    Generic[Properties, References], _BM25GenerateBase[ConnectionSync, Properties, References]
):
    pass
