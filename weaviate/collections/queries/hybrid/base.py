from typing import Generic

from weaviate.collections.classes.types import Properties, References
from weaviate.collections.queries.hybrid.executors import (
    _HybridGenerateExecutor,
    _HybridQueryExecutor,
)
from weaviate.connect.v4 import ConnectionType


class _HybridGenerateBase(
    Generic[ConnectionType, Properties, References],
    _HybridGenerateExecutor[Properties, References],
):
    pass


class _HybridQueryBase(
    Generic[ConnectionType, Properties, References],
    _HybridQueryExecutor[Properties, References],
):
    pass
