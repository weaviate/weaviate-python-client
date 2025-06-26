from typing import Generic

from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.fetch_objects_by_ids.query.executor import (
    _FetchObjectsByIDsQueryExecutor,
)
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync


@executor.wrap("async")
class _FetchObjectsByIDsQueryAsync(
    Generic[Properties, References],
    _FetchObjectsByIDsQueryExecutor[ConnectionAsync, Properties, References],
):
    pass
