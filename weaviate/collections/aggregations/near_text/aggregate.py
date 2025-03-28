from weaviate.connect import impl
from weaviate.collections.aggregations.near_text.base import _NearTextBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@impl.wrap("async")
class _NearTextAsync(_NearTextBase[ConnectionAsync]):
    pass


@impl.wrap("sync")
class _NearText(_NearTextBase[ConnectionSync]):
    pass
