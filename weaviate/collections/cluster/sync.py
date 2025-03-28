from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync
from weaviate.collections.cluster.base import _ClusterBase


@executor.wrap("sync")
class _Cluster(_ClusterBase[ConnectionSync]):
    pass
