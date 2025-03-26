from weaviate.connect import impl
from weaviate.collections.aggregations.near_object.base import _NearObjectBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@impl.generate("async")
class _NearObjectAsync(_NearObjectBase[ConnectionAsync]):
    pass


@impl.generate("sync")
class _NearObject(_NearObjectBase[ConnectionSync]):
    pass
