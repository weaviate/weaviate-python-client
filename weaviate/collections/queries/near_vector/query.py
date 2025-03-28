from typing import Generic

from weaviate.connect import impl
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_vector.base import _NearVectorQueryBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@impl.wrap("async")
class _NearVectorQueryAsync(
    Generic[Properties, References], _NearVectorQueryBase[ConnectionAsync, Properties, References]
):
    pass


@impl.wrap("sync")
class _NearVectorQuery(
    Generic[Properties, References], _NearVectorQueryBase[ConnectionSync, Properties, References]
):
    pass
