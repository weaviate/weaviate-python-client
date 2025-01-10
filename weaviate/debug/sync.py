from weaviate import syncify
from weaviate.debug.debug import _DebugAsync


@syncify.convert
class _Debug(_DebugAsync):
    pass
