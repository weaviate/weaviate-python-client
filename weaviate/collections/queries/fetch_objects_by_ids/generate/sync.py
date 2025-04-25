from typing import Generic

from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.fetch_objects_by_ids.generate.executor import (
    _FetchObjectsByIDsGenerateExecutor,
)
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync


@executor.wrap("sync")
class _FetchObjectsByIDsGenerate(
    Generic[Properties, References],
    _FetchObjectsByIDsGenerateExecutor[ConnectionSync, Properties, References],
):
    pass
