from typing import Generic

from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_media.generate.executor import (
    _NearMediaGenerateExecutor,
)
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync


@executor.wrap("sync")
class _NearMediaGenerate(
    Generic[Properties, References],
    _NearMediaGenerateExecutor[ConnectionSync, Properties, References],
):
    pass
