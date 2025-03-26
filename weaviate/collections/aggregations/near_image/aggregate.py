from weaviate.connect import impl
from weaviate.collections.aggregations.near_image.base import _NearImageBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@impl.generate("async")
class _NearImageAsync(_NearImageBase[ConnectionAsync]):
    pass


@impl.generate("sync")
class _NearImage(_NearImageBase[ConnectionSync]):
    pass
