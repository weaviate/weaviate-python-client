from weaviate import asyncify
from weaviate.backup.backup import _BackupAsync


@asyncify.convert
class _Backup(_BackupAsync):
    pass
