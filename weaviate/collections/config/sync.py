from weaviate import syncify
from weaviate.connect.v4 import ConnectionSync
from weaviate.collections.config.async_ import _ConfigCollectionAsync, _ConfigCollectionBase


@syncify.convert(_ConfigCollectionAsync)
class _ConfigCollection(_ConfigCollectionBase[ConnectionSync]):
    pass
