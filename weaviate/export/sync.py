from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync
from weaviate.export.executor import _ExportExecutor


@executor.wrap("sync")
class _Export(_ExportExecutor[ConnectionSync]):
    pass
