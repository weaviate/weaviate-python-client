from weaviate import asyncify
from weaviate.collections.backups.backups import _CollectionBackupAsync


@asyncify.convert
class _CollectionBackup(_CollectionBackupAsync):
    pass
