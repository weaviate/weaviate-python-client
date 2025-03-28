from weaviate.connect import executor
from weaviate.collections.backups.base import _CollectionBackupBase
from weaviate.connect.v4 import ConnectionSync


@executor.wrap("sync")
class _CollectionBackup(_CollectionBackupBase[ConnectionSync]):
    pass
