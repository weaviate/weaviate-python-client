"""
Backup class definition.
"""

from abc import abstractmethod
from typing import Generic, Optional, Union, List

from weaviate.backup.backup_location import BackupLocationType
from weaviate.backup.executor import (
    _BackupExecutor,
    BackupStorage,
    BackupConfigCreate,
    BackupReturn,
    BackupStatusReturn,
    BackupConfigRestore,
)
from weaviate.connect.executor import ExecutorResult
from weaviate.connect.v4 import ConnectionType


class _BackupBase(Generic[ConnectionType]):
    _executor = _BackupExecutor()

    def __init__(self, connection: ConnectionType):
        self._connection: ConnectionType = connection

    @abstractmethod
    def create(
        self,
        backup_id: str,
        backend: BackupStorage,
        include_collections: Optional[Union[List[str], str]] = None,
        exclude_collections: Optional[Union[List[str], str]] = None,
        wait_for_completion: bool = False,
        config: Optional[BackupConfigCreate] = None,
        backup_location: Optional[BackupLocationType] = None,
    ) -> ExecutorResult[BackupReturn]:
        """Create a backup of all/per collection Weaviate objects.

        Parameters
        ----------
        backup_id : str
            The identifier name of the backup.
            NOTE: Case insensitive.
        backend : BackupStorage
            The backend storage where to create the backup.
        include_collections : Union[List[str], str], optional
            The collection/list of collections to be included in the backup. If not specified all
            collections will be included. Either `include_collections` or `exclude_collections` can be set. By default None.
        exclude_collections : Union[List[str], str], optional
            The collection/list of collections to be excluded in the backup.
            Either `include_collections` or `exclude_collections` can be set. By default None.
        wait_for_completion : bool, optional
            Whether to wait until the backup is done. By default False.
        config: BackupConfigCreate, optional
            The configuration of the backup creation. By default None.
        backup_location:
            The dynamic location of a backup. By default None.

        Returns
        -------
         A `_BackupReturn` object that contains the backup creation response.

        Raises
        ------
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        TypeError
            One of the arguments have a wrong type.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_create_status(
        self,
        backup_id: str,
        backend: BackupStorage,
        backup_location: Optional[BackupLocationType] = None,
    ) -> ExecutorResult[BackupStatusReturn]:
        """
        Checks if a started backup job has completed.

        Parameters
        ----------
        backup_id : str
            The identifier name of the backup.
            NOTE: Case insensitive.
        backend : BackupStorage eNUM
            The backend storage where the backup was created.
        backup_location: BackupLocationType
            The dynamic location of a backup. By default None.

        Returns
        -------
         A `BackupStatusReturn` object that contains the backup creation status response.
        """
        raise NotImplementedError()

    @abstractmethod
    def restore(
        self,
        backup_id: str,
        backend: BackupStorage,
        include_collections: Union[List[str], str, None] = None,
        exclude_collections: Union[List[str], str, None] = None,
        wait_for_completion: bool = False,
        config: Optional[BackupConfigRestore] = None,
        backup_location: Optional[BackupLocationType] = None,
    ) -> ExecutorResult[BackupReturn]:
        """
        Restore a backup of all/per collection Weaviate objects.

        Parameters
        ----------
        backup_id : str
            The identifier name of the backup.
            NOTE: Case insensitive.
        backend : BackupStorage
            The backend storage from where to restore the backup.
        include_collections : Union[List[str], str], optional
            The collection/list of collections to be included in the backup restore. If not specified all
            collections will be included (that were backup-ed). Either `include_collections` or
            `exclude_collections` can be set. By default None.
        exclude_collections : Union[List[str], str], optional
            The collection/list of collections to be excluded in the backup restore.
            Either `include_collections` or `exclude_collections` can be set. By default None.
        wait_for_completion : bool, optional
            Whether to wait until the backup restore is done.
        config: BackupConfigRestore, optional
            The configuration of the backup restoration. By default None.
        backup_location:
            The dynamic location of a backup. By default None.

        Returns
        -------
         A `BackupReturn` object that contains the backup restore response.

        Raises
        ------
        requests.ConnectionError
            If the network connection to weaviate fails.
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.
        """
        raise NotImplementedError()

    @abstractmethod
    def get_restore_status(
        self,
        backup_id: str,
        backend: BackupStorage,
        backup_location: Optional[BackupLocationType] = None,
    ) -> ExecutorResult[BackupStatusReturn]:
        """
        Checks if a started restore job has completed.

        Parameters
        ----------
        backup_id:
            The identifier name of the backup.
            NOTE: Case insensitive.
        backend:
            The backend storage where to create the backup.
        backup_location:
            The dynamic location of a backup. By default None.

        Returns
        -------
         A `BackupStatusReturn` object that contains the backup restore status response.
        """
        raise NotImplementedError()

    @abstractmethod
    def cancel(
        self,
        backup_id: str,
        backend: BackupStorage,
        backup_location: Optional[BackupLocationType] = None,
    ) -> ExecutorResult[bool]:
        """
        Cancels a running backup.

        Parameters
        ----------
        backup_id:
            The identifier name of the backup.
            NOTE: Case insensitive.
        backend:
            The backend storage where to create the backup.
        backup_location:
            The dynamic location of a backup. By default None.

        Raises
        ------
        weaviate.UnexpectedStatusCodeException
            If weaviate reports a none OK status.

        Returns
        -------
         A bool indicating if the cancellation was successful.
        """
        raise NotImplementedError()

    # did not make it into 1.27, will come later
    # async def list_backups(self, backend: BackupStorage) -> List[BackupReturn]:
    #     """
    #     List all backups that are currently in progress.
    #
    #     Parameters
    #     ----------
    #     backend : BackupStorage
    #         The backend storage where to create the backup.
    #
    #     Returns
    #     -------
    #      A list of `BackupStatusReturn` objects that contain the backup restore status responses.
    #     """
    #     return await self.__list_backups(backend)
