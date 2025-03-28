from weaviate.connect import impl
from weaviate.connect.v4 import ConnectionSync
from weaviate.debug.base import _DebugBase


@impl.wrap("sync")
class _Debug(_DebugBase[ConnectionSync]):
    pass
