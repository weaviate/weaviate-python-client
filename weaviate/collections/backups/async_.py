from weaviate.connect import executor
from weaviate.collections.backups.executor import _CollectionBackupExecutor
from weaviate.connect.v4 import ConnectionAsync


@executor.wrap("async")
class _CollectionBackupAsync(_CollectionBackupExecutor[ConnectionAsync]):
    pass
