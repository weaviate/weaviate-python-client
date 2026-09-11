from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync
from weaviate.tokenization.executor import _TokenizationExecutor


@executor.wrap("sync")
class _Tokenization(_TokenizationExecutor[ConnectionSync]):
    pass
