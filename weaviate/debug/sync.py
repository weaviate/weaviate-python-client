from weaviate import syncify
from weaviate.connect.v4 import ConnectionSync
from weaviate.debug.async_ import _DebugAsync
from weaviate.debug.base import _DebugBase


@syncify.convert(_DebugAsync)
class _Debug(_DebugBase[ConnectionSync]):
    pass
