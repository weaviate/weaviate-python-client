from weaviate.backup.backup import (
    _Backup,
    _BackupStatusReturn,
    BackupStorage,
)
from weaviate.connect import HttpxConnection as Connection


class _CollectionBackup:
    """Backup functionatility for this collection."""

    def __init__(self, connection: Connection, name: str):
        self._connection = connection
        self._name = name
        self._backup = _Backup(connection)

    def create(
        self, backup_id: str, backend: BackupStorage, wait_for_completion: bool = False
    ) -> _BackupStatusReturn:
        """Create a backup of this collection.

        Parameters
        ----------
        backup_id : str
            The identifier name of the backup. NOTE: Case insensitive.
        backend : BackupStorage
            The backend storage where to create the backup.
        wait_for_completion : bool, optional
            Whether to wait until the backup is done. By default False.

        Returns
        -------
         A `_BackupStatusReturn` object that contains the backup creation response.

        Raises
        ------
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        TypeError
            One of the arguments have a wrong type.
        """
        create = self._backup.create(backup_id, backend, [self._name], None, wait_for_completion)
        return _BackupStatusReturn(status=create.status, path=create.path)

    def restore(
        self, backup_id: str, backend: BackupStorage, wait_for_completion: bool = False
    ) -> _BackupStatusReturn:
        """
        Restore a backup of all/per class Weaviate objects.

        Parameters
        ----------
        backup_id : str
            The identifier name of the backup.
            NOTE: Case insensitive.
        backend : BackupStorage
            The backend storage from where to restore the backup.
        wait_for_completion : bool, optional
            Whether to wait until the backup restore is done.

        Returns
        -------
         A `_BackupStatusReturn` object that contains the backup restore response.

        Raises
        ------
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """
        restore = self._backup.restore(backup_id, backend, [self._name], None, wait_for_completion)
        return _BackupStatusReturn(status=restore.status, path=restore.path)

    def get_create_status(self, backup_id: str, backend: BackupStorage) -> _BackupStatusReturn:
        """Check if a started backup job has completed.

        Parameters
        ----------
        backup_id : str
            The identifier name of the backup.
            NOTE: Case insensitive.
        backend : BackupStorage eNUM
            The backend storage where the backup was created.

        Returns
        -------
         A `__BackupStatusReturn` object that contains the backup creation status response.
        """
        return self._backup.get_create_status(backup_id, backend)

    def get_restore_status(self, backup_id: str, backend: BackupStorage) -> _BackupStatusReturn:
        """Check if a started classification job has completed.

        Parameters
        ----------
        backup_id : str
            The identifier name of the backup.
            NOTE: Case insensitive.
        backend : BackupStorage
            The backend storage where to create the backup.

        Returns
        -------
         A `__BackupStatusReturn` object that contains the backup restore status response.
        """
        return self._backup.get_restore_status(backup_id, backend)
