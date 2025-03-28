from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync
from weaviate.collections.config.base import _ConfigCollectionBase


@executor.wrap("sync")
class _ConfigCollection(_ConfigCollectionBase[ConnectionSync]):
    pass
