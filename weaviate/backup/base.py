"""
Backup class definition.
"""

from typing import Generic

from weaviate.backup.executor import _BackupExecutor
from weaviate.connect.v4 import ConnectionType


class _BackupBase(Generic[ConnectionType]):
    _executor = _BackupExecutor()

    def __init__(self, connection: ConnectionType):
        self._connection: ConnectionType = connection
