from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.fetch_objects_by_ids.executors import (
    _FetchObjectsByIdsGenerateExecutor,
)
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@executor.wrap("async")
class _FetchObjectsByIDsGenerateAsync(
    Generic[Properties, References],
    _FetchObjectsByIdsGenerateExecutor[ConnectionAsync, Properties, References],
):
    pass


@executor.wrap("sync")
class _FetchObjectsByIDsGenerate(
    Generic[Properties, References],
    _FetchObjectsByIdsGenerateExecutor[ConnectionSync, Properties, References],
):
    pass
