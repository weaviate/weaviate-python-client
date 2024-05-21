from typing import Optional

from weaviate.backup.backup import (
    BackupConfigCreate,
    BackupConfigRestore,
    BackupStatusReturn,
    BackupStorage,
)
from weaviate.event_loop import _EventLoop
from weaviate.collections.backups.asy import _CollectionBackupAsync


class _CollectionBackup:
    """Backup functionality for this collection."""

    def __init__(self, event_loop: _EventLoop, backup: _CollectionBackupAsync):
        self.__backup = backup
        self.__event_loop = event_loop

    def create(
        self,
        backup_id: str,
        backend: BackupStorage,
        wait_for_completion: bool = False,
        config: Optional[BackupConfigCreate] = None,
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
        return self.__event_loop.run_until_complete(
            self.__backup.create, backup_id, backend, wait_for_completion, config
        )

    def restore(
        self,
        backup_id: str,
        backend: BackupStorage,
        wait_for_completion: bool = False,
        config: Optional[BackupConfigRestore] = None,
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
                Whether to wait until the backup restore is done.
            `config`
                The configuration for the backup restoration. By default None.

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
        return self.__event_loop.run_until_complete(
            self.__backup.restore, backup_id, backend, wait_for_completion, config
        )

    def get_create_status(self, backup_id: str, backend: BackupStorage) -> BackupStatusReturn:
        """Check if a started backup job has completed.

        Arguments:
            `backup_id`
                The identifier name of the backup.
                NOTE: Case insensitive.
            `backend`
                The backend storage where the backup was created.

        Returns:
            A `BackupStatusReturn` object that contains the backup creation status response.
        """
        return self.__event_loop.run_until_complete(
            self.__backup.get_create_status, backup_id, backend
        )

    def get_restore_status(self, backup_id: str, backend: BackupStorage) -> BackupStatusReturn:
        """Check if a started classification job has completed.

        Arguments:
            `backup_id`
                The identifier name of the backup.
                NOTE: Case insensitive.
            `backend`
                The backend storage where to create the backup.

        Returns:
            A `BackupStatusReturn` object that contains the backup restore status response.
        """
        return self.__event_loop.run_until_complete(
            self.__backup.get_restore_status, backup_id, backend
        )
