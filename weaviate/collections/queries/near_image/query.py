from typing import Generic

from weaviate.connect import impl
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_image.base import _NearImageQueryBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@impl.generate("async")
class _NearImageQueryAsync(
    Generic[Properties, References], _NearImageQueryBase[ConnectionAsync, Properties, References]
):
    pass


@impl.generate("sync")
class _NearImageQuery(
    Generic[Properties, References], _NearImageQueryBase[ConnectionSync, Properties, References]
):
    pass
