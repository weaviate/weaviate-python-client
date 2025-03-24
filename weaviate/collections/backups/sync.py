from weaviate import syncify
from weaviate.collections.backups.backups import _CollectionBackupAsync, _CollectionBackupBase
from weaviate.connect.v4 import ConnectionSync


@syncify.convert(_CollectionBackupAsync)
class _CollectionBackup(_CollectionBackupBase[ConnectionSync]):
    pass
