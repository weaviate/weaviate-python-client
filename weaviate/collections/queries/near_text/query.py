from typing import Generic

from weaviate.connect import impl
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_text.base import _NearTextQueryBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@impl.generate("async")
class _NearTextQueryAsync(
    Generic[Properties, References], _NearTextQueryBase[ConnectionAsync, Properties, References]
):
    pass


@impl.generate("sync")
class _NearTextQuery(
    Generic[Properties, References], _NearTextQueryBase[ConnectionSync, Properties, References]
):
    pass
