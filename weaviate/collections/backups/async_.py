from weaviate.connect import executor
from weaviate.collections.backups.base import _CollectionBackupBase
from weaviate.connect.v4 import ConnectionAsync


@executor.wrap("async")
class _CollectionBackupAsync(_CollectionBackupBase[ConnectionAsync]):
    pass
