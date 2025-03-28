from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_object.base import _NearObjectGenerateBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@executor.wrap("async")
class _NearObjectGenerateAsync(
    Generic[Properties, References],
    _NearObjectGenerateBase[ConnectionAsync, Properties, References],
):
    pass


@executor.wrap("sync")
class _NearObjectGenerate(
    Generic[Properties, References], _NearObjectGenerateBase[ConnectionSync, Properties, References]
):
    pass
