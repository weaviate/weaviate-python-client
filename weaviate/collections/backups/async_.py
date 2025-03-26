from weaviate.connect import impl
from weaviate.collections.backups.base import _CollectionBackupBase
from weaviate.connect.v4 import ConnectionAsync


@impl.generate("async")
class _CollectionBackupAsync(_CollectionBackupBase[ConnectionAsync]):
    pass
