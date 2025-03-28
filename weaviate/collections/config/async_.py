from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync
from weaviate.collections.config.base import _ConfigCollectionBase


@executor.wrap("async")
class _ConfigCollectionAsync(_ConfigCollectionBase[ConnectionAsync]):
    pass
