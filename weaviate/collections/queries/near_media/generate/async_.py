from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_media.generate.executor import _NearMediaGenerateExecutor
from weaviate.connect.v4 import ConnectionAsync


@executor.wrap("async")
class _NearMediaGenerateAsync(
    Generic[Properties, References],
    _NearMediaGenerateExecutor[ConnectionAsync, Properties, References],
):
    pass
