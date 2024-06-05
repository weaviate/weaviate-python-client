from weaviate import syncify
from weaviate.collections.config.config import _ConfigCollectionAsync


@syncify.convert
class _ConfigCollection(_ConfigCollectionAsync):
    pass
