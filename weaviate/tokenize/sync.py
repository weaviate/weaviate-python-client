from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync
from weaviate.tokenize.executor import _TokenizeExecutor


@executor.wrap("sync")
class _Tokenize(_TokenizeExecutor[ConnectionSync]):
    pass
