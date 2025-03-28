from weaviate.connect import impl
from weaviate.collections.aggregations.near_image.base import _NearImageBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@impl.wrap("async")
class _NearImageAsync(_NearImageBase[ConnectionAsync]):
    pass


@impl.wrap("sync")
class _NearImage(_NearImageBase[ConnectionSync]):
    pass
