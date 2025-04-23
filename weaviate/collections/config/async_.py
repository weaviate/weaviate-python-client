from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync
from weaviate.collections.config.executor import _ConfigCollectionExecutor


@executor.wrap("async")
class _ConfigCollectionAsync(_ConfigCollectionExecutor[ConnectionAsync]):
    pass
