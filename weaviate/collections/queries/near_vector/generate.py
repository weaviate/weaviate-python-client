from typing import Generic

from weaviate.connect import impl
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_vector.base import _NearVectorGenerateBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@impl.generate("async")
class _NearVectorGenerateAsync(
    Generic[Properties, References],
    _NearVectorGenerateBase[ConnectionAsync, Properties, References],
):
    pass


@impl.generate("sync")
class _NearVectorGenerate(
    Generic[Properties, References], _NearVectorGenerateBase[ConnectionSync, Properties, References]
):
    pass
