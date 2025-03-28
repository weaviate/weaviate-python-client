from weaviate.collections.aggregations.near_vector.base import _NearVectorBase
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@executor.wrap("async")
class _NearVectorAsync(_NearVectorBase[ConnectionAsync]):
    pass


@executor.wrap("sync")
class _NearVector(_NearVectorBase[ConnectionSync]):
    pass
