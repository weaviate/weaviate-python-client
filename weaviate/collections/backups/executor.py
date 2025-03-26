from typing import Optional

from weaviate.backup.executor import (
    BackupConfigCreate,
    BackupConfigRestore,
    BackupReturn,
    BackupStatusReturn,
    BackupStorage,
)
from weaviate.backup.executor import _BackupExecutor
from weaviate.backup.backup_location import BackupLocationType
from weaviate.connect.executor import execute, ExecutorResult
from weaviate.connect.v4 import ConnectionType


class _CollectionBackupExecutor:
    _executor = _BackupExecutor()

    def __init__(self, name: str) -> None:
        self._name = name

    def create(
        self,
        backup_id: str,
        backend: BackupStorage,
        wait_for_completion: bool = False,
        config: Optional[BackupConfigCreate] = None,
        backup_location: Optional[BackupLocationType] = None,
        *,
        connection: ConnectionType
    ) -> ExecutorResult[BackupStatusReturn]:
        def resp(res: BackupReturn) -> BackupStatusReturn:
            return BackupStatusReturn(
                error=res.error, status=res.status, path=res.path, id=backup_id
            )

        return execute(
            response_callback=resp,
            method=self._executor.create,
            connection=connection,
            backup_id=backup_id,
            backend=backend,
            include_collections=[self._name],
            exclude_collections=None,
            wait_for_completion=wait_for_completion,
            config=config,
            backup_location=backup_location,
        )

    def restore(
        self,
        backup_id: str,
        backend: BackupStorage,
        wait_for_completion: bool = False,
        config: Optional[BackupConfigRestore] = None,
        backup_location: Optional[BackupLocationType] = None,
        *,
        connection: ConnectionType
    ) -> ExecutorResult[BackupStatusReturn]:
        def resp(res: BackupReturn) -> BackupStatusReturn:
            return BackupStatusReturn(
                error=res.error, status=res.status, path=res.path, id=backup_id
            )

        return execute(
            response_callback=resp,
            method=self._executor.restore,
            connection=connection,
            backup_id=backup_id,
            backend=backend,
            include_collections=[self._name],
            exclude_collections=None,
            wait_for_completion=wait_for_completion,
            config=config,
            backup_location=backup_location,
        )

    def get_create_status(
        self,
        backup_id: str,
        backend: BackupStorage,
        backup_location: Optional[BackupLocationType] = None,
        *,
        connection: ConnectionType
    ) -> ExecutorResult[BackupStatusReturn]:
        return self._executor.get_create_status(
            connection=connection,
            backup_id=backup_id,
            backend=backend,
            backup_location=backup_location,
        )

    def get_restore_status(
        self,
        backup_id: str,
        backend: BackupStorage,
        backup_location: Optional[BackupLocationType] = None,
        *,
        connection: ConnectionType
    ) -> ExecutorResult[BackupStatusReturn]:
        return self._executor.get_restore_status(
            connection=connection,
            backup_id=backup_id,
            backend=backend,
            backup_location=backup_location,
        )
