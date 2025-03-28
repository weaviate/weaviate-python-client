from weaviate.connect import impl
from weaviate.collections.aggregations.near_object.base import _NearObjectBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@impl.wrap("async")
class _NearObjectAsync(_NearObjectBase[ConnectionAsync]):
    pass


@impl.wrap("sync")
class _NearObject(_NearObjectBase[ConnectionSync]):
    pass
