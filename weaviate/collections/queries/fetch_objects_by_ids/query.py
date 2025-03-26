from typing import Generic

from weaviate.connect import impl
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.fetch_object_by_id.base import _FetchObjectByIDQueryBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@impl.generate("async")
class _FetchObjectsByIDsQueryAsync(
    Generic[Properties, References],
    _FetchObjectByIDQueryBase[ConnectionAsync, Properties, References],
):
    pass


@impl.generate("sync")
class _FetchObjectsByIDsQuery(
    Generic[Properties, References],
    _FetchObjectByIDQueryBase[ConnectionSync, Properties, References],
):
    pass
