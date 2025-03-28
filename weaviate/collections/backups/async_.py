from weaviate.connect import impl
from weaviate.collections.backups.base import _CollectionBackupBase
from weaviate.connect.v4 import ConnectionAsync


@impl.wrap("async")
class _CollectionBackupAsync(_CollectionBackupBase[ConnectionAsync]):
    pass
