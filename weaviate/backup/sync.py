from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionSync
from weaviate.backup.base import _BackupBase


@executor.wrap("sync")
class _Backup(_BackupBase[ConnectionSync]):
    pass
