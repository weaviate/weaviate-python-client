from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_vector.query.executor import _NearVectorQueryExecutor
from weaviate.connect.v4 import ConnectionSync


@executor.wrap("sync")
class _NearVectorQuery(
    Generic[Properties, References],
    _NearVectorQueryExecutor[ConnectionSync, Properties, References],
):
    pass
