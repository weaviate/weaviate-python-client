from typing import Generic

from weaviate.connect import impl
from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.hybrid.base import _HybridQueryBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@impl.generate("async")
class _HybridQueryAsync(
    Generic[Properties, References], _HybridQueryBase[ConnectionAsync, Properties, References]
):
    pass


@impl.generate("sync")
class _HybridQuery(
    Generic[Properties, References], _HybridQueryBase[ConnectionSync, Properties, References]
):
    pass
