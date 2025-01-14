from typing import Optional

from weaviate.backup.backup import (
    BackupConfigCreate,
    BackupConfigRestore,
    BackupStatusReturn,
    BackupStorage,
)
from weaviate.backup.backup import (
    _BackupAsync,
)
from weaviate.backup.backup_location import BackupLocationType
from weaviate.connect import ConnectionV4


class _CollectionBackupBase:
    """Backup functionality for this collection."""

    def __init__(self, connection: ConnectionV4, name: str):
        self._connection = connection
        self._name = name
        self._backup = _BackupAsync(connection)


class _CollectionBackupAsync(_CollectionBackupBase):
    """Backup functionality for this collection."""

    async def create(
        self,
        backup_id: str,
        backend: BackupStorage,
        wait_for_completion: bool = False,
        config: Optional[BackupConfigCreate] = None,
        backup_location: Optional[BackupLocationType] = None,
    ) -> BackupStatusReturn:
        """Create a backup of this collection.

        Arguments:
            `backup_id`
                The identifier name of the backup. NOTE: Case insensitive.
            `backend`
                The backend storage where to create the backup.
            `wait_for_completion`
                Whether to wait until the backup is done. By default False.
            `config`
                The configuration for the backup creation. By default None.
            `backup_location`:
                The dynamic location of a backup. By default None.

        Returns:
            A `BackupStatusReturn` object that contains the backup creation response.

        Raises:
            `weaviate.WeaviateConnectionError`
                If the network connection to weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If weaviate reports a none OK status.
            `weaviate.BackupFailedError`
                If the backup failed.
            `TypeError`
                One of the arguments have a wrong type.
        """
        create = await self._backup.create(
            backup_id, backend, [self._name], None, wait_for_completion, config, backup_location
        )
        return BackupStatusReturn(
            error=create.error, status=create.status, path=create.path, id=backup_id
        )

    async def restore(
        self,
        backup_id: str,
        backend: BackupStorage,
        wait_for_completion: bool = False,
        config: Optional[BackupConfigRestore] = None,
        backup_location: Optional[BackupLocationType] = None,
    ) -> BackupStatusReturn:
        """
        Restore a backup of all/per class Weaviate objects.

        Arguments:
            `backup_id`
                The identifier name of the backup.
                NOTE: Case insensitive.
            `backend`
                The backend storage from where to restore the backup.
            `wait_for_completion`
                Whether to wait until the backup restore is done. By default False.
            `config`
                The configuration for the backup restoration. By default None.
            `backup_location`:
                The dynamic location of a backup. By default None.

        Returns:
            A `BackupStatusReturn` object that contains the backup restore response.

        Raises:
            `weaviate.WeaviateConnectionError`
                If the network connection to weaviate fails.
            `weaviate.UnexpectedStatusCodeError`
                If weaviate reports a none OK status.
            `weaviate.BackupFailedError`
                If the backup failed.
        """
        restore = await self._backup.restore(
            backup_id, backend, [self._name], None, wait_for_completion, config, backup_location
        )
        return BackupStatusReturn(
            error=restore.error, status=restore.status, path=restore.path, id=backup_id
        )

    async def get_create_status(
        self,
        backup_id: str,
        backend: BackupStorage,
        backup_location: Optional[BackupLocationType] = None,
    ) -> BackupStatusReturn:
        """Check if a started backup job has completed.

        Arguments:
            `backup_id`
                The identifier name of the backup.
                NOTE: Case insensitive.
            `backend`
                The backend storage where the backup was created.
            `backup_location`:
                The dynamic location of a backup. By default None.

        Returns:
            A `BackupStatusReturn` object that contains the backup creation status response.
        """
        return await self._backup.get_create_status(backup_id, backend, backup_location)

    async def get_restore_status(
        self,
        backup_id: str,
        backend: BackupStorage,
        backup_location: Optional[BackupLocationType] = None,
    ) -> BackupStatusReturn:
        """Check if a started classification job has completed.

        Arguments:
            `backup_id`
                The identifier name of the backup.
                NOTE: Case insensitive.
            `backend`
                The backend storage where to create the backup.
            `backup_location`:
                The dynamic location of a backup. By default None.

        Returns:
            A `BackupStatusReturn` object that contains the backup restore status response.
        """
        return await self._backup.get_restore_status(backup_id, backend, backup_location)
