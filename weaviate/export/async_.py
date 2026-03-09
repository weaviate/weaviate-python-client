from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync
from weaviate.export.executor import _ExportExecutor


@executor.wrap("async")
class _ExportAsync(_ExportExecutor[ConnectionAsync]):
    pass
