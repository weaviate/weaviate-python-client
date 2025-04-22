from typing import (
    Generic,
)

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.fetch_object_by_id.executor import _FetchObjectByIDQueryExecutor
from weaviate.connect.v4 import ConnectionAsync


@executor.wrap("async")
class _FetchObjectByIDQueryAsync(
    Generic[Properties, References],
    _FetchObjectByIDQueryExecutor[ConnectionAsync, Properties, References],
):
    pass
