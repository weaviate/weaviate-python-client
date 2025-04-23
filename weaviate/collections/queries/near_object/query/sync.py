from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_object.query.executor import _NearObjectQueryExecutor
from weaviate.connect.v4 import ConnectionSync


@executor.wrap("sync")
class _NearObjectQuery(
    Generic[Properties, References],
    _NearObjectQueryExecutor[ConnectionSync, Properties, References],
):
    pass
