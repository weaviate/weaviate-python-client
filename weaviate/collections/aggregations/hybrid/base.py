from typing import Generic

from weaviate.collections.aggregations.hybrid.executor import _HybridExecutor
from weaviate.connect.v4 import ConnectionType


class _HybridBase(Generic[ConnectionType], _HybridExecutor):
    pass
