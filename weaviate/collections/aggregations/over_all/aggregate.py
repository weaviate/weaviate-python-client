from weaviate.connect import executor
from weaviate.collections.aggregations.over_all.executor import _OverAllExecutor
from weaviate.connect.v4 import ConnectionAsync, ConnectionSync


@executor.wrap("async")
class _OverAllAsync(_OverAllExecutor[ConnectionAsync]):
    pass


@executor.wrap("sync")
class _OverAll(_OverAllExecutor[ConnectionSync]):
    pass
