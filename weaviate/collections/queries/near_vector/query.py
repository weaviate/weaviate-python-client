from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_vector.base import _NearVectorQueryBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@executor.wrap("async")
class _NearVectorQueryAsync(
    Generic[Properties, References], _NearVectorQueryBase[ConnectionAsync, Properties, References]
):
    pass


@executor.wrap("sync")
class _NearVectorQuery(
    Generic[Properties, References], _NearVectorQueryBase[ConnectionSync, Properties, References]
):
    pass
