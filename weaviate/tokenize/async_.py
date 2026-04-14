from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync
from weaviate.tokenize.executor import _TokenizeExecutor


@executor.wrap("async")
class _TokenizeAsync(_TokenizeExecutor[ConnectionAsync]):
    pass
