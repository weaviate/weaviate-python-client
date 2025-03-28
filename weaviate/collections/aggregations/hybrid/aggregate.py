from weaviate.connect import executor
from weaviate.collections.aggregations.hybrid.base import _HybridBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@executor.wrap("async")
class _HybridAsync(_HybridBase[ConnectionAsync]):
    pass


@executor.wrap("sync")
class _Hybrid(_HybridBase[ConnectionSync]):
    pass
