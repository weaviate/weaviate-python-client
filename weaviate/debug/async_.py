from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync
from weaviate.debug.executor import _DebugExecutor


@executor.wrap("async")
class _DebugAsync(_DebugExecutor[ConnectionAsync]):
    pass
