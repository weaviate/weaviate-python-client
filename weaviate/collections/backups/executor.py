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


class _CollectionBackupExecutor(Generic[ConnectionType]):
    def __init__(self, connection: ConnectionType, name: str) -> None:
        self._executor = _BackupExecutor(connection)
        self._name = name

    def create(
        self,
        backup_id: str,
        backend: BackupStorage,
        wait_for_completion: bool = False,
        config: Optional[BackupConfigCreate] = None,
        backup_location: Optional[BackupLocationType] = None,
    ) -> executor.Result[BackupStatusReturn]:
        """Create a backup of this collection.

        Args:
            backup_id: The identifier name of the backup. NOTE: Case insensitive.
            backend: The backend storage where to create the backup.
            wait_for_completion: Whether to wait until the backup is done. By default False.
            config: The configuration for the backup creation. By default None.
            backup_location`: The dynamic location of a backup. By default None.

        Returns:
            A `BackupStatusReturn` object that contains the backup creation response.

        Raises:
            weaviate.exceptions.WeaviateConnectionError: If the network connection to weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If weaviate reports a none OK status.
            weaviate.BackupFailedError: If the backup failed.
            TypeError: One of the arguments have a wrong type.
        """

        def resp(res: BackupReturn) -> BackupStatusReturn:
            return BackupStatusReturn(
                error=res.error, status=res.status, path=res.path, id=backup_id
            )

        return executor.execute(
            response_callback=resp,
            method=self._executor.create,
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
    ) -> executor.Result[BackupStatusReturn]:
        """Restore a backup of all/per class Weaviate objects.

        Args:
            backup_id: The identifier name of the backup. NOTE: Case insensitive.
            backend: The backend storage from where to restore the backup.
            wait_for_completion: Whether to wait until the backup restore is done. By default False.
            config: The configuration for the backup restoration. By default None.
            backup_location`: The dynamic location of a backup. By default None.

        Returns:
            A `BackupStatusReturn` object that contains the backup restore response.

        Raises:
            weaviate.exceptions.WeaviateConnectionError: If the network connection to weaviate fails.
            weaviate.exceptions.UnexpectedStatusCodeError: If weaviate reports a none OK status.
            weaviate.BackupFailedError: If the backup failed.
        """

        def resp(res: BackupReturn) -> BackupStatusReturn:
            return BackupStatusReturn(
                error=res.error, status=res.status, path=res.path, id=backup_id
            )

        return executor.execute(
            response_callback=resp,
            method=self._executor.restore,
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
    ) -> executor.Result[BackupStatusReturn]:
        """Check if a started backup job has completed.

        Args:
            backup_id: The identifier name of the backup. NOTE: Case insensitive.
            backend: The backend storage where the backup was created.
            backup_location`: The dynamic location of a backup. By default None.

        Returns:
            A `BackupStatusReturn` object that contains the backup creation status response.
        """
        return self._executor.get_create_status(
            backup_id=backup_id,
            backend=backend,
            backup_location=backup_location,
        )

    def get_restore_status(
        self,
        backup_id: str,
        backend: BackupStorage,
        backup_location: Optional[BackupLocationType] = None,
    ) -> executor.Result[BackupStatusReturn]:
        """Check if a started classification job has completed.

        Args:
            backup_id: The identifier name of the backup. NOTE: Case insensitive.
            backend: The backend storage where to create the backup.
            backup_location`: The dynamic location of a backup. By default None.

        Returns:
            A `BackupStatusReturn` object that contains the backup restore status response.
        """
        return self._executor.get_restore_status(
            backup_id=backup_id,
            backend=backend,
            backup_location=backup_location,
        )
