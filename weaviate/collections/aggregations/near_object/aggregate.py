from weaviate.connect import executor
from weaviate.collections.aggregations.near_object.base import _NearObjectBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@executor.wrap("async")
class _NearObjectAsync(_NearObjectBase[ConnectionAsync]):
    pass


@executor.wrap("sync")
class _NearObject(_NearObjectBase[ConnectionSync]):
    pass
