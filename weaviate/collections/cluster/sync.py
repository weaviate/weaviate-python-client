from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync
from weaviate.collections.cluster.executor import _ClusterExecutor


@executor.wrap("sync")
class _Cluster(_ClusterExecutor[ConnectionSync]):
    pass
