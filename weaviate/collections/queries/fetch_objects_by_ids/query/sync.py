from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.fetch_objects_by_ids.query.executor import (
    _FetchObjectsByIDsQueryExecutor,
)
from weaviate.connect.v4 import ConnectionSync


@executor.wrap("sync")
class _FetchObjectsByIDsQuery(
    Generic[Properties, References],
    _FetchObjectsByIDsQueryExecutor[ConnectionSync, Properties, References],
):
    pass
