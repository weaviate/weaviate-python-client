from weaviate.connect import executor
from weaviate.collections.aggregations.hybrid.executor import _HybridExecutor
from weaviate.connect.v4 import ConnectionAsync


@executor.wrap("async")
class _HybridAsync(_HybridExecutor[ConnectionAsync]):
    pass
