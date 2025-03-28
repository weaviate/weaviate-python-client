from weaviate.connect import impl
from weaviate.connect.v4 import ConnectionSync
from weaviate.collections.cluster.base import _ClusterBase


@impl.wrap("sync")
class _Cluster(_ClusterBase[ConnectionSync]):
    pass
