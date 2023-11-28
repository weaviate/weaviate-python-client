from weaviate.backup.backup import (
    _Backup,
    _BackupStatusReturn,
    BackupStorage,
)
from weaviate.connect.connection import Connection


class _CollectionBackup:
    """Backup functionatility for this collection."""

    def __init__(self, connection: Connection, name: str):
        self._connection = connection
        self._name = name
        self._backup = _Backup(connection)

    def create(
        self, backup_id: str, backend: BackupStorage, wait_for_completion: bool = False
    ) -> _BackupStatusReturn:
        create = self._backup.create(backup_id, backend, self._name, None, wait_for_completion)
        return _BackupStatusReturn(status=create.status, path=create.path)

    def restore(
        self, backup_id: str, backend: BackupStorage, wait_for_completion: bool = False
    ) -> _BackupStatusReturn:
        restore = self._backup.restore(backup_id, backend, self._name, None, wait_for_completion)
        return _BackupStatusReturn(status=restore.status, path=restore.path)

    def get_create_status(self, backup_id: str, backend: BackupStorage) -> _BackupStatusReturn:
        return self._backup.get_create_status(backup_id, backend)

    def get_restore_status(self, backup_id: str, backend: BackupStorage) -> _BackupStatusReturn:
        return self._backup.get_restore_status(backup_id, backend)
