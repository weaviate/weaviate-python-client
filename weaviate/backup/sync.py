from weaviate.backup.executor import _BackupExecutor
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync


@executor.wrap("sync")
class _Backup(_BackupExecutor[ConnectionSync]):
    pass
