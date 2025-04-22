from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_image.query.executor import _NearImageQueryExecutor
from weaviate.connect.v4 import ConnectionAsync


@executor.wrap("async")
class _NearImageQueryAsync(
    Generic[Properties, References],
    _NearImageQueryExecutor[ConnectionAsync, Properties, References],
):
    pass
