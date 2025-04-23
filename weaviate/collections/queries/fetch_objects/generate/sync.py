from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.fetch_objects.generate.executor import (
    _FetchObjectsGenerateExecutor,
)
from weaviate.connect.v4 import ConnectionSync


@executor.wrap("sync")
class _FetchObjectsGenerate(
    Generic[Properties, References],
    _FetchObjectsGenerateExecutor[ConnectionSync, Properties, References],
):
    pass
