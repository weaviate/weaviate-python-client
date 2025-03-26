from weaviate.connect import impl
from weaviate.connect.v4 import ConnectionAsync
from weaviate.collections.config.base import _ConfigCollectionBase


@impl.generate("async")
class _ConfigCollectionAsync(_ConfigCollectionBase[ConnectionAsync]):
    pass
