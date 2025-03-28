from typing import (
    Generic,
)

from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.fetch_object_by_id.executor import _FetchObjectsByIdQueryExecutor
from weaviate.connect.v4 import ConnectionType


class _FetchObjectByIDQueryBase(
    Generic[ConnectionType, Properties, References],
    _FetchObjectsByIdQueryExecutor[Properties, References],
):
    pass
