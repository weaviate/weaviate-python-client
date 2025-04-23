from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.bm25.query.executor import _BM25QueryExecutor
from weaviate.connect.v4 import ConnectionAsync


@executor.wrap("async")
class _BM25QueryAsync(
    Generic[Properties, References], _BM25QueryExecutor[ConnectionAsync, Properties, References]
):
    pass
