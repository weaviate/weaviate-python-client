from weaviate.connect import impl
from weaviate.connect.v4 import ConnectionAsync
from weaviate.collections.cluster.base import _ClusterBase


@impl.generate("async")
class _ClusterAsync(_ClusterBase[ConnectionAsync]):
    pass
