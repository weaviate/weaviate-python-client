from weaviate.collections.aggregations.near_vector.base import _NearVectorBase
from weaviate.connect import impl
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@impl.generate("async")
class _NearVectorAsync(_NearVectorBase[ConnectionAsync]):
    pass


@impl.generate("sync")
class _NearVector(_NearVectorBase[ConnectionSync]):
    pass
