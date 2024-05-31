from weaviate.backup.backup import (
    _BackupAsync,
)
from weaviate.connect import ConnectionV4


class _CollectionBackupBase:
    """Backup functionality for this collection."""

    def __init__(self, connection: ConnectionV4, name: str):
        self._connection = connection
        self._name = name
        self._backup = _BackupAsync(connection)
