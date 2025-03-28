from typing import Generic

from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.fetch_objects_by_ids.executors import (
    _FetchObjectsByIdsGenerateExecutor,
    _FetchObjectsByIdsQueryExecutor,
)
from weaviate.connect.v4 import ConnectionType


class _FetchObjectsByIDsGenerateBase(
    Generic[ConnectionType, Properties, References],
    _FetchObjectsByIdsGenerateExecutor[Properties, References],
):
    pass


class _FetchObjectsByIDsQueryBase(
    Generic[ConnectionType, Properties, References],
    _FetchObjectsByIdsQueryExecutor[Properties, References],
):
    pass
