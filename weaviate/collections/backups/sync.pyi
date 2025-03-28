from typing import Optional
from weaviate.backup.executor import (
    BackupConfigCreate,
    BackupConfigRestore,
    BackupStatusReturn,
    BackupStorage,
    BackupLocationType,
)
from weaviate.collections.backups.base import _CollectionBackupBase
from weaviate.connect.v4 import ConnectionSync

class _CollectionBackup(_CollectionBackupBase[ConnectionSync]):
    def create(
        self,
        backup_id: str,
        backend: BackupStorage,
        wait_for_completion: bool = False,
        config: Optional[BackupConfigCreate] = None,
        backup_location: Optional[BackupLocationType] = None,
    ) -> BackupStatusReturn: ...
    def restore(
        self,
        backup_id: str,
        backend: BackupStorage,
        wait_for_completion: bool = False,
        config: Optional[BackupConfigRestore] = None,
        backup_location: Optional[BackupLocationType] = None,
    ) -> BackupStatusReturn: ...
    def get_create_status(
        self,
        backup_id: str,
        backend: BackupStorage,
        backup_location: Optional[BackupLocationType] = None,
    ) -> BackupStatusReturn: ...
    def get_restore_status(
        self,
        backup_id: str,
        backend: BackupStorage,
        backup_location: Optional[BackupLocationType] = None,
    ) -> BackupStatusReturn: ...
