from typing import Generic

from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.fetch_objects.executors import (
    _FetchObjectsGenerateExecutor,
    _FetchObjectsQueryExecutor,
)
from weaviate.connect.v4 import ConnectionType


class _FetchObjectsGenerateBase(
    Generic[ConnectionType, Properties, References],
    _FetchObjectsGenerateExecutor[Properties, References],
):
    pass


class _FetchObjectsQueryBase(
    Generic[ConnectionType, Properties, References],
    _FetchObjectsQueryExecutor[Properties, References],
):
    pass
