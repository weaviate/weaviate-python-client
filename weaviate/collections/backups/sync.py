from weaviate import asyncify
from weaviate.collections.backups.async_ import _CollectionBackupAsync


@asyncify.convert
class _CollectionBackup(_CollectionBackupAsync):
    pass
