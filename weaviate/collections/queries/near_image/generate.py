from typing import Generic

from weaviate.connect import impl
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_image.base import _NearImageGenerateBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@impl.generate("async")
class _NearImageGenerateAsync(
    Generic[Properties, References], _NearImageGenerateBase[ConnectionAsync, Properties, References]
):
    pass


@impl.generate("sync")
class _NearImageGenerate(
    Generic[Properties, References], _NearImageGenerateBase[ConnectionSync, Properties, References]
):
    pass
