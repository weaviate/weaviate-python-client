from weaviate import asyncify
from weaviate.collections.cluster.async_ import _ClusterAsync


@asyncify.convert
class _Cluster(_ClusterAsync):
    pass
