from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.fetch_objects.query.executor import _FetchObjectsQueryExecutor
from weaviate.connect.v4 import ConnectionSync


@executor.wrap("sync")
class _FetchObjectsQuery(
    Generic[Properties, References],
    _FetchObjectsQueryExecutor[ConnectionSync, Properties, References],
):
    pass
