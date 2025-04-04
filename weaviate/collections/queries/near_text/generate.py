from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_text.executors import _NearTextGenerateExecutor
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@executor.wrap("async")
class _NearTextGenerateAsync(
    Generic[Properties, References],
    _NearTextGenerateExecutor[ConnectionAsync, Properties, References],
):
    pass


@executor.wrap("sync")
class _NearTextGenerate(
    Generic[Properties, References],
    _NearTextGenerateExecutor[ConnectionSync, Properties, References],
):
    pass
