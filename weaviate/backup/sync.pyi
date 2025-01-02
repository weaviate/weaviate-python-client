from typing import Optional, Union, List

from weaviate.backup.backup import (
    BackupStorage,
    BackupReturn,
    BackupStatusReturn,
    BackupConfigCreate,
    BackupConfigRestore,
    BackupConfigCancel,
)
from weaviate.backup.dynamic_path import DynamicPathType
from weaviate.connect import ConnectionV4

class _Backup:
    """Backup class used to schedule and/or check the status of a backup process of Weaviate objects."""

    def __init__(self, connection: ConnectionV4):
        self._connection = connection

    def cancel(
        self,
        backup_id: str,
        backend: BackupStorage,
        config: Optional[Union[BackupConfigCancel, DynamicPathType]] = None,
    ) -> bool: ...
    def create(
        self,
        backup_id: str,
        backend: BackupStorage,
        include_collections: Optional[Union[List[str], str]] = None,
        exclude_collections: Optional[Union[List[str], str]] = None,
        wait_for_completion: bool = False,
        config: Optional[Union[BackupConfigCreate, DynamicPathType]] = None,
    ) -> BackupReturn: ...
    def get_create_status(
        self, backup_id: str, backend: BackupStorage, config: Optional[DynamicPathType] = None
    ) -> BackupStatusReturn: ...
    def restore(
        self,
        backup_id: str,
        backend: BackupStorage,
        include_collections: Union[List[str], str, None] = None,
        exclude_collections: Union[List[str], str, None] = None,
        wait_for_completion: bool = False,
        config: Optional[Union[BackupConfigRestore, DynamicPathType]] = None,
    ) -> BackupReturn: ...
    def get_restore_status(
        self, backup_id: str, backend: BackupStorage, dynamic_path: Optional[DynamicPathType] = None
    ) -> BackupStatusReturn: ...
