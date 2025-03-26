from weaviate.connect import impl
from weaviate.connect.v4 import ConnectionAsync
from weaviate.debug.base import _DebugBase


@impl.generate("async")
class _DebugAsync(_DebugBase[ConnectionAsync]):
    pass
