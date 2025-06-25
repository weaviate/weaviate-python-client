from weaviate.collections.aggregations.near_vector.executor import _NearVectorExecutor
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync


@executor.wrap("sync")
class _NearVector(_NearVectorExecutor[ConnectionSync]):
    pass
