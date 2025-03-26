from typing import Generic

from weaviate.connect import impl
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.near_text.base import _NearTextGenerateBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@impl.generate("async")
class _NearTextGenerateAsync(
    Generic[Properties, References], _NearTextGenerateBase[ConnectionAsync, Properties, References]
):
    pass


@impl.generate("sync")
class _NearTextGenerate(
    Generic[Properties, References], _NearTextGenerateBase[ConnectionSync, Properties, References]
):
    pass
