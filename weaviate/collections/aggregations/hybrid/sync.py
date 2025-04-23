from weaviate.connect import executor
from weaviate.collections.aggregations.hybrid.executor import _HybridExecutor
from weaviate.connect.v4 import ConnectionSync


@executor.wrap("sync")
class _Hybrid(_HybridExecutor[ConnectionSync]):
    pass
