from weaviate.cluster.base import _ClusterExecutor
from weaviate.cluster.replicate import _Replicate
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync


@executor.wrap("sync")
class _Cluster(_ClusterExecutor[ConnectionSync]):
    def __init__(self, connection: ConnectionSync):
        super().__init__(connection)
        self.replications = _Replicate(connection)
