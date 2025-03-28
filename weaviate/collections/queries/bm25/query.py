from typing import Generic

from weaviate.connect import impl
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.bm25.base import _BM25QueryBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@impl.wrap("async")
class _BM25QueryAsync(
    Generic[Properties, References], _BM25QueryBase[ConnectionAsync, Properties, References]
):
    pass


@impl.wrap("sync")
class _BM25Query(
    Generic[Properties, References], _BM25QueryBase[ConnectionSync, Properties, References]
):
    pass
