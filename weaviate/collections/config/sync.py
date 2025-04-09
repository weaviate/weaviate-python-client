from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync
from weaviate.collections.config.executor import _ConfigExecutor


@executor.wrap("sync")
class _ConfigCollection(_ConfigExecutor[ConnectionSync]):
    pass
