from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionAsync
from weaviate.backup.base import _BackupBase


@executor.wrap("async")
class _BackupAsync(_BackupBase[ConnectionAsync]):
    pass
