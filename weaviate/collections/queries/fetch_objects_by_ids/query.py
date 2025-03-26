from typing import Generic

from weaviate.connect import impl
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.fetch_objects_by_ids.base import _FetchObjectsByIDsQueryBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@impl.generate("async")
class _FetchObjectsByIDsQueryAsync(
    Generic[Properties, References],
    _FetchObjectsByIDsQueryBase[ConnectionAsync, Properties, References],
):
    pass


@impl.generate("sync")
class _FetchObjectsByIDsQuery(
    Generic[Properties, References],
    _FetchObjectsByIDsQueryBase[ConnectionSync, Properties, References],
):
    pass
