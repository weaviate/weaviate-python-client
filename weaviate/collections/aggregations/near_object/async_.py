from weaviate.connect import executor
from weaviate.collections.aggregations.near_object.executor import _NearObjectExecutor
from weaviate.connect.v4 import ConnectionAsync


@executor.wrap("async")
class _NearObjectAsync(_NearObjectExecutor[ConnectionAsync]):
    pass
