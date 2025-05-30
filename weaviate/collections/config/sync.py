from weaviate.collections.config.executor import _ConfigCollectionExecutor
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync


@executor.wrap("sync")
class _ConfigCollection(_ConfigCollectionExecutor[ConnectionSync]):
    pass
