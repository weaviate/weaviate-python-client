from weaviate import syncify
from weaviate.collections.backups.backups import _CollectionBackupAsync


@syncify.convert
class _CollectionBackup(_CollectionBackupAsync):
    pass
