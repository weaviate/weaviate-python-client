from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_image.generate.executor import _NearImageGenerateExecutor
from weaviate.connect.v4 import ConnectionSync


@executor.wrap("sync")
class _NearImageGenerate(
    Generic[Properties, References],
    _NearImageGenerateExecutor[ConnectionSync, Properties, References],
):
    pass
