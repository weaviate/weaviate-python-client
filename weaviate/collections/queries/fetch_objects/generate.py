from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.fetch_objects.base import _FetchObjectsGenerateBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@executor.wrap("async")
class _FetchObjectsGenerateAsync(
    Generic[Properties, References],
    _FetchObjectsGenerateBase[ConnectionAsync, Properties, References],
):
    pass


@executor.wrap("sync")
class _FetchObjectsGenerate(
    Generic[Properties, References],
    _FetchObjectsGenerateBase[ConnectionSync, Properties, References],
):
    pass
