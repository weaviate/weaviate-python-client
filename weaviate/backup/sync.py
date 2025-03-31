from weaviate.connect import executor
from weaviate.backup.executor import _BackupExecutor


@executor.wrap("sync")
class _Backup(_BackupExecutor):
    pass
