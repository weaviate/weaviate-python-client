from typing import Optional, Union, List

from weaviate.backup.base import _BackupBase
from weaviate.backup.executor import (
    BackupStorage,
    BackupReturn,
    BackupStatusReturn,
    BackupConfigCreate,
    BackupConfigRestore,
    _BackupExecutor,
)
from weaviate.backup.backup_location import BackupLocationType
from weaviate.connect.v4 import ConnectionSync

class _Backup(_BackupExecutor[ConnectionSync]):
    """Backup class used to schedule and/or check the status of a backup process of Weaviate objects."""

    def cancel(
        self,
        backup_id: str,
        backend: BackupStorage,
        backup_location: Optional[BackupLocationType] = None,
    ) -> bool: ...
    def create(
        self,
        backup_id: str,
        backend: BackupStorage,
        include_collections: Optional[Union[List[str], str]] = None,
        exclude_collections: Optional[Union[List[str], str]] = None,
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
        wait_for_completion: bool = False,
        config: Optional[BackupConfigRestore] = None,
        backup_location: Optional[BackupLocationType] = None,
    ) -> BackupReturn: ...
    def get_restore_status(
        self,
        backup_id: str,
        backend: BackupStorage,
        backup_location: Optional[BackupLocationType] = None,
    ) -> BackupStatusReturn: ...
