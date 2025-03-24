from typing import Optional
from weaviate.backup.backup import (
    BackupConfigCreate,
    BackupConfigRestore,
    BackupStatusReturn,
    BackupStorage,
)
from weaviate.collections.backups.backups import _CollectionBackupBase
from weaviate.connect.v4 import ConnectionSync

class _CollectionBackup(_CollectionBackupBase[ConnectionSync]):
    def create(
        self,
        backup_id: str,
        backend: BackupStorage,
        wait_for_completion: bool = False,
        config: Optional[BackupConfigCreate] = None,
    ) -> BackupStatusReturn: ...
    def restore(
        self,
        backup_id: str,
        backend: BackupStorage,
        wait_for_completion: bool = False,
        config: Optional[BackupConfigRestore] = None,
    ) -> BackupStatusReturn: ...
    def get_create_status(self, backup_id: str, backend: BackupStorage) -> BackupStatusReturn: ...
    def get_restore_status(self, backup_id: str, backend: BackupStorage) -> BackupStatusReturn: ...
