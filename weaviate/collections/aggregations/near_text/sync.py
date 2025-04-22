from weaviate.connect import executor
from weaviate.collections.aggregations.near_text.executor import _NearTextExecutor
from weaviate.connect.v4 import ConnectionSync


@executor.wrap("sync")
class _NearText(_NearTextExecutor[ConnectionSync]):
    pass
