from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_vector.base import _NearVectorGenerateBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@executor.wrap("async")
class _NearVectorGenerateAsync(
    Generic[Properties, References],
    _NearVectorGenerateBase[ConnectionAsync, Properties, References],
):
    pass


@executor.wrap("sync")
class _NearVectorGenerate(
    Generic[Properties, References], _NearVectorGenerateBase[ConnectionSync, Properties, References]
):
    pass
