from weaviate.cluster.base import _ClusterExecutor
from weaviate.cluster.replicate import _ReplicateAsync
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync


@executor.wrap("async")
class _ClusterAsync(_ClusterExecutor[ConnectionAsync]):
    def __init__(self, connection: ConnectionAsync):
        super().__init__(connection)
        self.replications = _ReplicateAsync(connection)
