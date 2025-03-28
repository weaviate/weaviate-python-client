from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync
from weaviate.debug.base import _DebugBase


@executor.wrap("sync")
class _Debug(_DebugBase[ConnectionSync]):
    pass
