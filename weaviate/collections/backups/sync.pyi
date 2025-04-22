from typing import Generic, Optional
from weaviate.backup.executor import (
    BackupConfigCreate,
    BackupConfigRestore,
    BackupReturn,
    BackupStatusReturn,
    BackupStorage,
    _BackupExecutor,
)
from weaviate.backup.backup_location import BackupLocationType
from weaviate.connect import executor
from weaviate.connect.v4 import ConnectionType
from weaviate.connect.v4 import ConnectionSync
from .executor import _CollectionBackupExecutor

class _CollectionBackup(_CollectionBackupExecutor[ConnectionSync]):
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
