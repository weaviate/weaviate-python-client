from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_image.generate.executor import _NearImageGenerateExecutor
from weaviate.connect.v4 import ConnectionAsync


@executor.wrap("async")
class _NearImageGenerateAsync(
    Generic[Properties, References],
    _NearImageGenerateExecutor[ConnectionAsync, Properties, References],
):
    pass
