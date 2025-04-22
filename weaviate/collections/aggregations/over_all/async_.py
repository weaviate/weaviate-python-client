from weaviate.connect import executor
from weaviate.collections.aggregations.over_all.executor import _OverAllExecutor
from weaviate.connect.v4 import ConnectionAsync


@executor.wrap("async")
class _OverAllAsync(_OverAllExecutor[ConnectionAsync]):
    pass
