from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync
from weaviate.collections.cluster.base import _ClusterBase


@executor.wrap("async")
class _ClusterAsync(_ClusterBase[ConnectionAsync]):
    pass
