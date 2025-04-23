from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.bm25.query.executor import _BM25QueryExecutor
from weaviate.connect.v4 import ConnectionSync


@executor.wrap("sync")
class _BM25Query(
    Generic[Properties, References], _BM25QueryExecutor[ConnectionSync, Properties, References]
):
    pass
