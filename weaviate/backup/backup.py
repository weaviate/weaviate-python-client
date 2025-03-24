"""
Backup class definition.
"""

from typing import Generic, Optional, Union, List, Tuple

from weaviate.backup.backup_location import BackupLocationType
from weaviate.backup.executor import (
    _BackupExecutor,
    BackupStorage,
    BackupConfigCreate,
    BackupReturn,
    BackupStatusReturn,
    BackupConfigRestore,
    STORAGE_NAMES,
)
from weaviate.connect.executor import aresult
from weaviate.connect.v4 import ConnectionAsync, ConnectionType
from weaviate.util import (
    _capitalize_first_letter,
)


class _BackupBase(Generic[ConnectionType]):
    _executor = _BackupExecutor()

    def __init__(self, connection: ConnectionType):
        self._connection: ConnectionType = connection


class _BackupAsync(_BackupBase[ConnectionAsync]):
    """Backup class used to schedule and/or check the status of a backup process of Weaviate objects."""

    async def create(
        self,
        backup_id: str,
        backend: BackupStorage,
        include_collections: Optional[Union[List[str], str]] = None,
        exclude_collections: Optional[Union[List[str], str]] = None,
        wait_for_completion: bool = False,
        config: Optional[BackupConfigCreate] = None,
        backup_location: Optional[BackupLocationType] = None,
    ) -> BackupReturn:
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
        return await aresult(
            self._executor.create(
                connection=self._connection,
                backup_id=backup_id,
                backend=backend,
                include_collections=include_collections,
                exclude_collections=exclude_collections,
                wait_for_completion=wait_for_completion,
                config=config,
                backup_location=backup_location,
            )
        )

    async def get_create_status(
        self,
        backup_id: str,
        backend: BackupStorage,
        backup_location: Optional[BackupLocationType] = None,
    ) -> BackupStatusReturn:
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
        return await aresult(
            self._executor.get_create_status(
                connection=self._connection,
                backup_id=backup_id,
                backend=backend,
                backup_location=backup_location,
            )
        )

    async def restore(
        self,
        backup_id: str,
        backend: BackupStorage,
        include_collections: Union[List[str], str, None] = None,
        exclude_collections: Union[List[str], str, None] = None,
        wait_for_completion: bool = False,
        config: Optional[BackupConfigRestore] = None,
        backup_location: Optional[BackupLocationType] = None,
    ) -> BackupReturn:
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
        return await aresult(
            self._executor.restore(
                connection=self._connection,
                backup_id=backup_id,
                backend=backend,
                include_collections=include_collections,
                exclude_collections=exclude_collections,
                wait_for_completion=wait_for_completion,
                config=config,
                backup_location=backup_location,
            )
        )

    async def get_restore_status(
        self,
        backup_id: str,
        backend: BackupStorage,
        backup_location: Optional[BackupLocationType] = None,
    ) -> BackupStatusReturn:
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
        return await aresult(
            self._executor.get_restore_status(
                connection=self._connection,
                backup_id=backup_id,
                backend=backend,
                backup_location=backup_location,
            )
        )

    async def cancel(
        self,
        backup_id: str,
        backend: BackupStorage,
        backup_location: Optional[BackupLocationType] = None,
    ) -> bool:
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
        return await aresult(
            self._executor.cancel(
                connection=self._connection,
                backup_id=backup_id,
                backend=backend,
                backup_location=backup_location,
            )
        )

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


def _get_and_validate_create_restore_arguments(
    backup_id: str,
    backend: Union[str, BackupStorage],
    include_classes: Union[List[str], str, None],
    exclude_classes: Union[List[str], str, None],
    wait_for_completion: bool,
) -> Tuple[str, BackupStorage, List[str], List[str]]:
    """
    Validate and return the Backup.create/Backup.restore arguments.

    Parameters
    ----------
    backup_id : str
        The identifier name of the backup.
    backend : str
        The backend storage. Currently available options are:
            "filesystem", "s3", "gcs" and "azure".
    include_classes : Union[List[str], str, None]
        The class/list of classes to be included in the backup. If not specified all classes
        will be included. Either `include_classes` or `exclude_classes` can be set.
    exclude_classes : Union[List[str], str, None]
        The class/list of classes to be excluded from the backup.
        Either `include_classes` or `exclude_classes` can be set.
    wait_for_completion : bool
        Whether to wait until the backup restore is done.

    Returns
    -------
    Tuple[str, str, List[str], List[str]]
        Validated and processed (backup_id, backend, include_classes, exclude_classes).

    Raises
    ------
    TypeError
        One of the arguments have a wrong type.
    ValueError
        'backend' does not have an accepted value.
    """

    if not isinstance(backup_id, str):
        raise TypeError(f"'backup_id' must be of type str. Given type: {type(backup_id)}.")
    if isinstance(backend, str):
        try:
            backend = BackupStorage(backend.lower())
        except KeyError:
            raise ValueError(
                f"'backend' must have one of these values: {STORAGE_NAMES}. "
                f"Given value: {backend}."
            )

    if not isinstance(wait_for_completion, bool):
        raise TypeError(
            f"'wait_for_completion' must be of type bool. Given type: {type(wait_for_completion)}."
        )

    if include_classes is not None:
        if isinstance(include_classes, str):
            include_classes = [include_classes]
        elif not isinstance(include_classes, list):
            raise TypeError(
                "'include_classes' must be of type str, list of str or None. "
                f"Given type: {type(include_classes)}."
            )
    else:
        include_classes = []

    if exclude_classes is not None:
        if isinstance(exclude_classes, str):
            exclude_classes = [exclude_classes]
        elif not isinstance(exclude_classes, list):
            raise TypeError(
                "'exclude_classes' must be of type str, list of str or None. "
                f"Given type: {type(exclude_classes)}."
            )
    else:
        exclude_classes = []

    if include_classes and exclude_classes:
        raise TypeError("Either 'include_classes' OR 'exclude_classes' can be set, not both.")

    include_classes = [_capitalize_first_letter(cls) for cls in include_classes]
    exclude_classes = [_capitalize_first_letter(cls) for cls in exclude_classes]

    return (backup_id.lower(), backend, include_classes, exclude_classes)


def _get_and_validate_get_status(
    backup_id: str, backend: Union[str, BackupStorage]
) -> Tuple[str, BackupStorage]:
    """
    Checks if a started classification job has completed.

    Parameters
    ----------
    backup_id : str
        The identifier name of the backup.
        NOTE: Case insensitive.
    backend : str
        The backend storage where to create the backup. Currently available options are:
            "filesystem", "s3", "gcs" and "azure".

    Returns
    -------
    Tuple[str, str]
        Validated and processed (backup_id, backend, include_classes, exclude_classes).

    Raises
    ------
    TypeError
        One of the arguments is of a wrong type.
    """

    if not isinstance(backup_id, str):
        raise TypeError(f"'backup_id' must be of type str. Given type: {type(backup_id)}.")
    if isinstance(backend, str):
        try:
            backend = BackupStorage(backend.lower())
        except KeyError:
            raise ValueError(
                f"'backend' must have one of these values: {STORAGE_NAMES}. "
                f"Given value: {backend}."
            )

    return (backup_id.lower(), backend)
