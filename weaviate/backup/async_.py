from weaviate.connect import impl
from weaviate.connect.v4 import ConnectionAsync
from weaviate.backup.base import _BackupBase

from .executor import _BackupExecutor


@impl.generate("async")
class _BackupAsync(_BackupBase[ConnectionAsync], _BackupExecutor):
    pass
