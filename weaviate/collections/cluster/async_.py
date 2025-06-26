from weaviate.collections.cluster.executor import _ClusterExecutor
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync


@executor.wrap("async")
class _ClusterAsync(_ClusterExecutor[ConnectionAsync]):
    pass
