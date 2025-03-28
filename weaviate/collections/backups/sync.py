from weaviate.connect import impl
from weaviate.collections.backups.base import _CollectionBackupBase
from weaviate.connect.v4 import ConnectionSync


@impl.wrap("sync")
class _CollectionBackup(_CollectionBackupBase[ConnectionSync]):
    pass
