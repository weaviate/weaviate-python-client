from weaviate import syncify
from weaviate.collections.cluster.cluster import _ClusterAsync


@syncify.convert
class _Cluster(_ClusterAsync):
    pass
