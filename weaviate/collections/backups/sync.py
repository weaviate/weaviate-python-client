from weaviate import syncify
from weaviate.collections.backups.backups import _CollectionBackupAsync, _CollectionBackupBase


@syncify.convert_new(_CollectionBackupAsync)
class _CollectionBackup(_CollectionBackupBase):
    pass
