from weaviate import syncify
from weaviate.connect.v4 import ConnectionSync
from weaviate.backup.backup import _BackupAsync, _BackupBase


@syncify.convert(_BackupAsync)
class _Backup(_BackupBase[ConnectionSync]):
    pass
