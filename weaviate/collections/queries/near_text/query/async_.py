from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_text.query.executor import _NearTextQueryExecutor
from weaviate.connect.v4 import ConnectionAsync


@executor.wrap("async")
class _NearTextQueryAsync(
    Generic[Properties, References], _NearTextQueryExecutor[ConnectionAsync, Properties, References]
):
    pass
