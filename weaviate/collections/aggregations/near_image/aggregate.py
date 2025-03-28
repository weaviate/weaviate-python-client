from weaviate.connect import executor
from weaviate.collections.aggregations.near_image.base import _NearImageBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@executor.wrap("async")
class _NearImageAsync(_NearImageBase[ConnectionAsync]):
    pass


@executor.wrap("sync")
class _NearImage(_NearImageBase[ConnectionSync]):
    pass
