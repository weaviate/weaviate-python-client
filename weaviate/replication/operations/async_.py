from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync
from weaviate.replication.operations.executor import _OperationsExecutor


@executor.wrap("async")
class _OperationsAsync(_OperationsExecutor[ConnectionAsync]):
    pass
