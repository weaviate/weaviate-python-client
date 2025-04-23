from weaviate.connect import executor
from weaviate.collections.aggregations.near_image.executor import _NearImageExecutor
from weaviate.connect.v4 import ConnectionSync


@executor.wrap("sync")
class _NearImage(_NearImageExecutor[ConnectionSync]):
    pass
