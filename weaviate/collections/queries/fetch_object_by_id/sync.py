from typing import (
    Generic,
)

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.fetch_object_by_id.executor import _FetchObjectByIDQueryExecutor
from weaviate.connect.v4 import ConnectionSync


@executor.wrap("sync")
class _FetchObjectByIDQuery(
    Generic[Properties, References],
    _FetchObjectByIDQueryExecutor[ConnectionSync, Properties, References],
):
    pass
