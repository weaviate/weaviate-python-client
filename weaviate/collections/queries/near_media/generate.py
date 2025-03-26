from typing import Generic

from weaviate.connect import impl
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_media.base import _NearMediaGenerateBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@impl.generate("async")
class _NearMediaGenerateAsync(
    Generic[Properties, References], _NearMediaGenerateBase[ConnectionAsync, Properties, References]
):
    pass


@impl.generate("sync")
class _NearMediaGenerate(
    Generic[Properties, References], _NearMediaGenerateBase[ConnectionSync, Properties, References]
):
    pass
