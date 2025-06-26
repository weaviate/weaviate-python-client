from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync
from weaviate.debug.executor import _DebugExecutor


@executor.wrap("sync")
class _Debug(_DebugExecutor[ConnectionSync]):
    pass
