from typing import Generic

from weaviate.connect import impl
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_media.base import _NearMediaGenerateBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@impl.wrap("async")
class _NearMediaGenerateAsync(
    Generic[Properties, References], _NearMediaGenerateBase[ConnectionAsync, Properties, References]
):
    pass


@impl.wrap("sync")
class _NearMediaGenerate(
    Generic[Properties, References], _NearMediaGenerateBase[ConnectionSync, Properties, References]
):
    pass
