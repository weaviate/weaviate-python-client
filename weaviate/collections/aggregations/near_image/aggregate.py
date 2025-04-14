from weaviate.connect import executor
from weaviate.collections.aggregations.near_image.executor import _NearImageExecutor
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@executor.wrap("async")
class _NearImageAsync(_NearImageExecutor[ConnectionAsync]):
    pass


@executor.wrap("sync")
class _NearImage(_NearImageExecutor[ConnectionSync]):
    pass
