from weaviate.collections.cluster.executor import _ClusterExecutor
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync


@executor.wrap("sync")
class _Cluster(_ClusterExecutor[ConnectionSync]):
    pass
