from typing import Generic

from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_media.query.executor import (
    _NearMediaQueryExecutor,
)
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync


@executor.wrap("sync")
class _NearMediaQuery(
    Generic[Properties, References],
    _NearMediaQueryExecutor[ConnectionSync, Properties, References],
):
    pass
