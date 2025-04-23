from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_object.generate.executor import _NearObjectGenerateExecutor
from weaviate.connect.v4 import ConnectionAsync


@executor.wrap("async")
class _NearObjectGenerateAsync(
    Generic[Properties, References],
    _NearObjectGenerateExecutor[ConnectionAsync, Properties, References],
):
    pass
