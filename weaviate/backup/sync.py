from weaviate import syncify
from weaviate.backup.backup import _BackupAsync


@syncify.convert
class _Backup(_BackupAsync):
    pass
