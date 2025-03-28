from weaviate.connect import impl
from weaviate.connect.v4 import ConnectionAsync
from weaviate.backup.base import _BackupBase


@impl.wrap("async")
class _BackupAsync(_BackupBase[ConnectionAsync]):
    pass
