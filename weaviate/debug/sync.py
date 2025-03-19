from weaviate import syncify
from weaviate.connect.v4 import ConnectionSync
from weaviate.debug.debug import _DebugAsync, _DebugBase


@syncify.convert_new(_DebugAsync)
class _Debug(_DebugBase[ConnectionSync]):
    pass
