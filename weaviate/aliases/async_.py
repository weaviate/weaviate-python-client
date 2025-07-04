from weaviate.aliases.executor import _AliasExecutor
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync


@executor.wrap("async")
class _AliasAsync(_AliasExecutor[ConnectionAsync]):
    pass
