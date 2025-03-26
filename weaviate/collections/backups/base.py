from abc import abstractmethod
from typing import Generic, Optional

from weaviate.backup.executor import (
    BackupConfigCreate,
    BackupConfigRestore,
    BackupStatusReturn,
    BackupStorage,
)
from weaviate.backup.backup_location import BackupLocationType
from weaviate.collections.backups.executor import _CollectionBackupExecutor
from weaviate.connect.executor import ExecutorResult
from weaviate.connect.v4 import ConnectionType


class _CollectionBackupBase(Generic[ConnectionType]):
    """Backup functionality for this collection."""

    def __init__(self, connection: ConnectionType, name: str):
        self._connection: ConnectionType = connection
        self._executor = _CollectionBackupExecutor(name)

    @abstractmethod
    def create(
        self,
        backup_id: str,
        backend: BackupStorage,
        wait_for_completion: bool = False,
        config: Optional[BackupConfigCreate] = None,
        backup_location: Optional[BackupLocationType] = None,
    ) -> ExecutorResult[BackupStatusReturn]:
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
        raise NotImplementedError()

    @abstractmethod
    def restore(
        self,
        backup_id: str,
        backend: BackupStorage,
        wait_for_completion: bool = False,
        config: Optional[BackupConfigRestore] = None,
        backup_location: Optional[BackupLocationType] = None,
    ) -> ExecutorResult[BackupStatusReturn]:
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
        raise NotImplementedError()

    @abstractmethod
    def get_create_status(
        self,
        backup_id: str,
        backend: BackupStorage,
        backup_location: Optional[BackupLocationType] = None,
    ) -> ExecutorResult[BackupStatusReturn]:
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
        raise NotImplementedError()

    @abstractmethod
    def get_restore_status(
        self,
        backup_id: str,
        backend: BackupStorage,
        backup_location: Optional[BackupLocationType] = None,
    ) -> ExecutorResult[BackupStatusReturn]:
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
        raise NotImplementedError()
