from weaviate import syncify
from weaviate.connect.v4 import ConnectionSync
from weaviate.collections.cluster.async_ import _ClusterAsync, _ClusterBase


@syncify.convert(_ClusterAsync)
class _Cluster(_ClusterBase[ConnectionSync]):
    pass
