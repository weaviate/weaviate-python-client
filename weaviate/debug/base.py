from typing import Generic
from weaviate.connect.v4 import ConnectionType
from weaviate.debug.executor import _DebugExecutor


class _DebugBase(Generic[ConnectionType], _DebugExecutor):
    pass
