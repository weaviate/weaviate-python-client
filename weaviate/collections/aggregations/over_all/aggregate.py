from weaviate.connect import executor
from weaviate.collections.aggregations.over_all.base import _OverAllBase
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@executor.wrap("async")
class _OverAllAsync(_OverAllBase[ConnectionAsync]):
    pass


@executor.wrap("sync")
class _OverAll(_OverAllBase[ConnectionSync]):
    pass
