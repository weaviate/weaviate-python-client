from weaviate import asyncify
from weaviate.collections.config.config import _ConfigCollectionAsync


@asyncify.convert
class _ConfigCollection(_ConfigCollectionAsync):
    pass
