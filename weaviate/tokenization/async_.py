from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync
from weaviate.tokenization.executor import _TokenizationExecutor


@executor.wrap("async")
class _TokenizationAsync(_TokenizationExecutor[ConnectionAsync]):
    pass
