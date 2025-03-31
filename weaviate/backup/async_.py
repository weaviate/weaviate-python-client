from weaviate.connect import executor
from weaviate.backup.executor import _BackupExecutor


@executor.wrap("async")
class _BackupAsync(_BackupExecutor):
    pass
