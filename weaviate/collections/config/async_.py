from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync
from weaviate.collections.config.executor import _ConfigExecutor


@executor.wrap("async")
class _ConfigCollectionAsync(_ConfigExecutor[ConnectionAsync]):
    pass
