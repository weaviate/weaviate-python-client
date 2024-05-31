from weaviate import asyncify
from weaviate.collections.config.async_ import _ConfigCollectionAsync


@asyncify.convert
class _ConfigCollection(_ConfigCollectionAsync):
    pass
