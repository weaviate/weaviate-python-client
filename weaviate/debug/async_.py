from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync
from weaviate.debug.base import _DebugBase


@executor.wrap("async")
class _DebugAsync(_DebugBase[ConnectionAsync]):
    pass
