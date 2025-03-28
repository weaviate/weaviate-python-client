from typing import Generic

from weaviate.collections.backups.executor import _CollectionBackupExecutor
from weaviate.connect.v4 import ConnectionType


class _CollectionBackupBase(Generic[ConnectionType], _CollectionBackupExecutor):
    """Backup functionality for this collection."""

    def __init__(self, connection: ConnectionType, name: str):
        self._executor = _CollectionBackupExecutor(connection, name)
