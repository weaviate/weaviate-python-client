from typing import Generic

from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_vector.query.executor import (
    _NearVectorQueryExecutor,
)
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync


@executor.wrap("async")
class _NearVectorQueryAsync(
    Generic[Properties, References],
    _NearVectorQueryExecutor[ConnectionAsync, Properties, References],
):
    pass
