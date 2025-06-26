from typing import Generic

from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.fetch_objects.generate.executor import (
    _FetchObjectsGenerateExecutor,
)
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync


@executor.wrap("async")
class _FetchObjectsGenerateAsync(
    Generic[Properties, References],
    _FetchObjectsGenerateExecutor[ConnectionAsync, Properties, References],
):
    pass
