from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_media.base import _NearMediaQueryBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@executor.wrap("async")
class _NearMediaQueryAsync(
    Generic[Properties, References], _NearMediaQueryBase[ConnectionAsync, Properties, References]
):
    pass


@executor.wrap("sync")
class _NearMediaQuery(
    Generic[Properties, References], _NearMediaQueryBase[ConnectionSync, Properties, References]
):
    pass
