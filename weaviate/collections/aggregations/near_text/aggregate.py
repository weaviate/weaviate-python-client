from weaviate.connect import executor
from weaviate.collections.aggregations.near_text.base import _NearTextBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@executor.wrap("async")
class _NearTextAsync(_NearTextBase[ConnectionAsync]):
    pass


@executor.wrap("sync")
class _NearText(_NearTextBase[ConnectionSync]):
    pass
