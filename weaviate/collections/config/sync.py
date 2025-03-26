from weaviate.connect import impl
from weaviate.connect.v4 import ConnectionSync
from weaviate.collections.config.base import _ConfigCollectionBase


@impl.generate("sync")
class _ConfigCollection(_ConfigCollectionBase[ConnectionSync]):
    pass
