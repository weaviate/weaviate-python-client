from weaviate.backup.executor import _BackupExecutor
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync


@executor.wrap("async")
class _BackupAsync(_BackupExecutor[ConnectionAsync]):
    pass
