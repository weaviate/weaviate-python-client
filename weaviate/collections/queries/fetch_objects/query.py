from typing import Generic

from weaviate.connect import impl
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.fetch_objects.base import _FetchObjectsQueryBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@impl.generate("async")
class _FetchObjectsQueryAsync(
    Generic[Properties, References], _FetchObjectsQueryBase[ConnectionAsync, Properties, References]
):
    pass


@impl.generate("sync")
class _FetchObjectsQuery(
    Generic[Properties, References], _FetchObjectsQueryBase[ConnectionSync, Properties, References]
):
    pass
