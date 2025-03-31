from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync
from weaviate.backup.executor import _BackupExecutor


@executor.wrap("sync")
class _Backup(_BackupExecutor[ConnectionSync]):
    pass
