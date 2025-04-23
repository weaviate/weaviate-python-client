from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.fetch_objects_by_ids.generate.executor import (
    _FetchObjectsByIDsGenerateExecutor,
)
from weaviate.connect.v4 import ConnectionAsync


@executor.wrap("async")
class _FetchObjectsByIDsGenerateAsync(
    Generic[Properties, References],
    _FetchObjectsByIDsGenerateExecutor[ConnectionAsync, Properties, References],
):
    pass
