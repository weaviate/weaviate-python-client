from weaviate import asyncify
from weaviate.collections.cluster.cluster import _ClusterAsync


@asyncify.convert
class _Cluster(_ClusterAsync):
    pass
