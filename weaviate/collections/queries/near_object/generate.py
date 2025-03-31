from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_object.executors import _NearObjectGenerateExecutor
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@executor.wrap("async")
class _NearObjectGenerateAsync(
    Generic[Properties, References],
    _NearObjectGenerateExecutor[ConnectionAsync, Properties, References],
):
    pass


@executor.wrap("sync")
class _NearObjectGenerate(
    Generic[Properties, References],
    _NearObjectGenerateExecutor[ConnectionSync, Properties, References],
):
    pass
