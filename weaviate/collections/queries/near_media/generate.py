from typing import Generic

from weaviate.connect import executor
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_media.base import _NearMediaGenerateBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@executor.wrap("async")
class _NearMediaGenerateAsync(
    Generic[Properties, References], _NearMediaGenerateBase[ConnectionAsync, Properties, References]
):
    pass


@executor.wrap("sync")
class _NearMediaGenerate(
    Generic[Properties, References], _NearMediaGenerateBase[ConnectionSync, Properties, References]
):
    pass
