from typing import Generic

from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_object.query.executor import (
    _NearObjectQueryExecutor,
)
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync


@executor.wrap("async")
class _NearObjectQueryAsync(
    Generic[Properties, References],
    _NearObjectQueryExecutor[ConnectionAsync, Properties, References],
):
    pass
