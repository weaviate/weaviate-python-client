from weaviate.connect import impl
from weaviate.connect.v4 import ConnectionSync
from weaviate.backup.base import _BackupBase


@impl.generate("sync")
class _Backup(_BackupBase[ConnectionSync]):
    pass
