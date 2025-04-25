from weaviate.collections.aggregations.near_object.executor import _NearObjectExecutor
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync


@executor.wrap("sync")
class _NearObject(_NearObjectExecutor[ConnectionSync]):
    pass
