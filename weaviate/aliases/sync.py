from weaviate.aliases.executor import _AliasExecutor
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync


@executor.wrap("sync")
class _Alias(_AliasExecutor[ConnectionSync]):
    pass
