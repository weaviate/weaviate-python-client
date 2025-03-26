from typing import Generic

from weaviate.connect import impl
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.hybrid.base import _HybridGenerateBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@impl.generate("async")
class _HybridGenerateAsync(
    Generic[Properties, References], _HybridGenerateBase[ConnectionAsync, Properties, References]
):
    pass


@impl.generate("sync")
class _HybridGenerate(
    Generic[Properties, References], _HybridGenerateBase[ConnectionSync, Properties, References]
):
    pass
