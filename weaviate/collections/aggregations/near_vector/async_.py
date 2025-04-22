from weaviate.collections.aggregations.near_vector.executor import _NearVectorExecutor
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync


@executor.wrap("async")
class _NearVectorAsync(_NearVectorExecutor[ConnectionAsync]):
    pass
