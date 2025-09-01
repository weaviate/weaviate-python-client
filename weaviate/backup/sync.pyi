from typing import List, Literal, Optional, Union

from weaviate.backup.backup import (
    BackupConfigCreate,
    BackupConfigRestore,
    BackupListReturn,
    BackupReturn,
    BackupStatusReturn,
    BackupStorage,
)
from weaviate.backup.backup_location import BackupLocationType
from weaviate.connect.v4 import ConnectionSync

from .executor import _BackupExecutor

class _Backup(_BackupExecutor[ConnectionSync]):
    def create(
        self,
        backup_id: str,
        backend: BackupStorage,
        include_collections: Union[List[str], str, None] = None,
        exclude_collections: Union[List[str], str, None] = None,
        wait_for_completion: bool = False,
        config: Optional[BackupConfigCreate] = None,
        backup_location: Optional[BackupLocationType] = None,
    ) -> BackupReturn: ...
    def get_create_status(
        self,
        backup_id: str,
        backend: BackupStorage,
        backup_location: Optional[BackupLocationType] = None,
    ) -> BackupStatusReturn: ...
    def restore(
        self,
        backup_id: str,
        backend: BackupStorage,
        include_collections: Union[List[str], str, None] = None,
        exclude_collections: Union[List[str], str, None] = None,
        roles_restore: Optional[Literal["noRestore", "all"]] = None,
        users_restore: Optional[Literal["noRestore", "all"]] = None,
        wait_for_completion: bool = False,
        config: Optional[BackupConfigRestore] = None,
        backup_location: Optional[BackupLocationType] = None,
        overwrite_alias: bool = False,
    ) -> BackupReturn: ...
    def get_restore_status(
        self,
        backup_id: str,
        backend: BackupStorage,
        backup_location: Optional[BackupLocationType] = None,
    ) -> BackupStatusReturn: ...
    def cancel(
        self,
        backup_id: str,
        backend: BackupStorage,
        backup_location: Optional[BackupLocationType] = None,
    ) -> bool: ...
    def list_backups(self, backend: BackupStorage) -> List[BackupListReturn]: ...
