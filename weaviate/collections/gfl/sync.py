from weaviate import syncify
from weaviate.collections.gfl.gfl import _GFLAsync, _GFLBase


@syncify.convert
class _GFL(_GFLAsync, _GFLBase):
    pass
