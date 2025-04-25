from typing import Generic

from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_text.generate.executor import (
    _NearTextGenerateExecutor,
)
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync


@executor.wrap("async")
class _NearTextGenerateAsync(
    Generic[Properties, References],
    _NearTextGenerateExecutor[ConnectionAsync, Properties, References],
):
    pass
